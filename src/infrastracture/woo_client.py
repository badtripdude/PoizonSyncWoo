import aiohttp
from loguru import logger

from src.application.interfaces import WooCommerceClient


class AsyncWooClient(WooCommerceClient):
    # TODO: create WooProduct
    def __init__(self, url: str, consumer_key: str, consumer_secret: str):
        self.url = url.rstrip("/") + "/wp-json/wc/v3"
        self.auth = aiohttp.BasicAuth(consumer_key, consumer_secret)

    async def _request(self, method: str, endpoint: str, params=None, json=None) -> (int, dict | str):
        url = f"{self.url}/{endpoint}"
        async with aiohttp.ClientSession(auth=self.auth) as session:
            async with session.request(method, url, params=params, json=json) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                try:
                    if "application/json" in content_type:
                        data = await resp.json()
                    else:
                        data = await resp.text()
                except aiohttp.ContentTypeError:
                    data = await resp.text()

                if status >= 400:
                    logger.error(f"Ошибка API: {status} {method} {url} → {data}")

                return status, data

    async def get_product_by_sku(self, sku: str):
        status, products = await self._request("GET", "products", params={"sku": sku})
        return products[0] if status == 200 and products else None

    async def create_or_update_product(self, data: dict):
        existing = await self.get_product_by_sku(data.get("sku"))
        if existing:
            product_id = existing["id"]
            return await self._request("PUT", f"products/{product_id}", json=data)
        return await self._request("POST", "products", json=data)

    async def ensure_brand_exists(self, brand_name: str) -> dict:
        """
        Проверяет наличие бренда. Если нет — создает и возвращает ID.
        """
        # Проверяем по имени
        status, brands = await self._request(
            "GET",
            "products/brands",
            params={"search": brand_name}
        )

        if brands:
            return brands[0]

        # Если нет — создаем
        status, brand = await self._request(
            "POST",
            "products/brands",
            json={"name": brand_name, "slug": brand_name.lower().replace(" ", "-")}
        )

        return brand

    async def create_or_update_variable_product_with_variations(self, base_data: dict,
                                                                variations: list[dict]) -> (int, dict):
        # Получаем ID бренда
        brand_name = base_data.get("brand")
        brand = None
        if brand_name:
            brand = await self.ensure_brand_exists(brand_name)
        existing = await self.get_product_by_sku(base_data.get('sku'))
        options: list[str] = [v["attributes"][0]["option"] for v in variations]
        attr = await self.ensure_attribute_and_terms('pa_eu_size', tuple(options))

        attr = {
            "id": attr['id'],
            "name": attr['name'],  # TODO: не совпадает
            "variation": True,
            "visible": True,
            "options": options
        }
        product_data = {
            "slug": base_data['slug'],
            "name": base_data["name"],
            "sku": base_data.get("sku", ""),
            "description": base_data.get("description", ""),
            "images": base_data.get("images", []),
            "type": "variable",
            "stock_status": "instock",
            "manage_stock": False,
            "meta_data": [
                {
                    "key": "_poizon_spu_id",
                    "value": str(base_data.get('spu_id'))
                }],
            "categories": [
                {"id": await self.get_sneakers_category_id()}
            ],
            "attributes": [
                attr
            ],
        }
        # Добавляем бренд в данные
        if brand:
            product_data["brands"] = [brand]

        if existing:
            logger.info(f"Товар  `{product_data.get('name')}` существует, обновляем...")
            product_id = existing["id"]
            await self._request("PUT", f"products/{product_id}", json=product_data)

            await self.delete_all_existing_variations(product_id)

            status_code = 200
        else:
            status, product = await self._request("POST", "products", json=product_data)
            if status != 201:
                return status, product
            product_id = product["id"]
            status_code = 201

        await self.add_product_variations(product_id, variations)

        # Принудительно повторно сохраняем атрибуты, чтобы WooCommerce инициализировал вариации
        await self._request("PUT", f"products/{product_id}", json={"attributes": [attr]})

        await self._request("PUT", f"products/{product_id}", json={
            "attributes": [attr],
            "default_attributes": [
                {
                    "name": "pa_eu_size",
                    "option": attr["options"][0]  # первая доступная
                }
            ]
        })
        return status_code, {"id": product_id, "message": "Product created or updated with variations"}

    async def delete_all_existing_variations(self, product_id: int) -> tuple[int, dict]:
        existing_vars = await self.get_all_variations(product_id)
        if not existing_vars:
            return 200, {"message": "Нет вариаций для удаления"}

        payload = {
            "delete": [{"id": var["id"]} for var in existing_vars]
        }

        status, response = await self._request(
            "POST",
            f"products/{product_id}/variations/batch",
            json=payload
        )

        if status != 200:
            logger.warning(f"Не удалось удалить вариации: status={status}, response={response}")
        return status, response

    async def add_product_variations(self, product_id: int, variations: list[dict]) -> tuple[int, dict]:
        # Установим stock_status по умолчанию
        for variation in variations:
            variation.setdefault("stock_status", "instock")

        payload = {
            "create": variations
        }

        status, response = await self._request(
            "POST",
            f"products/{product_id}/variations/batch",
            json=payload
        )

        if status != 200:
            logger.warning(f"Не удалось добавить вариации: status={status}, response={response}")
        return status, response

    # @alru_cache(maxsize=128)
    async def ensure_attribute_and_terms(self, attribute_slug: str, terms: tuple[str]) -> dict:
        # Получить список глобальных атрибутов
        status, attributes = await self._request("GET", "products/attributes")
        attr: dict = next((a for a in attributes if a["slug"].lower() == attribute_slug.lower()), None)

        # Если атрибут не существует — создаем
        if not attr:
            status, attr = await self._request("POST", f"products/attributes", json={
                "name": attribute_slug,
                "type": "select",
                "has_archives": True
            })

        attr_id: int = attr["id"]
        # Получить текущие термины
        status, existing_terms = await self.get_all_attribute_terms(attr_id, per_page=100)
        existing_names = {t["name"].lower() for t in existing_terms}

        # Добавить отсутствующие термины
        for term in terms:
            if term.lower() not in existing_names:
                await self._request("POST", f"products/attributes/{attr_id}/terms", json={"name": term})

        return attr

    async def get_all_attribute_terms(self, attr_id: int, per_page: int = 100) -> (int, list[dict]):
        """
        Получает все термины атрибута WooCommerce с поддержкой пагинации.

        :param attr_id: ID атрибута
        :param per_page: Количество элементов на странице (макс. 100)
        :return: Список терминов (list[dict])
        """
        all_terms = []
        page = 1

        while True:
            status, terms_page = await self._request(
                "GET",
                f"products/attributes/{attr_id}/terms",
                params={"per_page": per_page, "page": page}
            )

            if status != 200:
                logger.error(f"Ошибка получения терминов для атрибута {attr_id}: {status}, {terms_page}")
                break

            if not terms_page:  # Пустой ответ → конец
                break

            all_terms.extend(terms_page)

            if len(terms_page) < per_page:
                break  # Последняя страница

            page += 1

        return status, all_terms

    async def get_sneakers_category_id(self):
        category_data = {
            "name": "Sneakers",
            "slug": "sneakers",
            "parent": 0  # 0 = корневая категория
        }
        resp = await self._request("GET", "products/categories", params={"slug": category_data["slug"]})
        if not resp[1]:  # не нашли
            _, new_cat = await self._request("POST", "products/categories", json=category_data)
            category_id = new_cat["id"]
        else:
            category_id = resp[1][0]["id"]
        return category_id

    async def get_all_spu_ids_by_brand(self, brand: str) -> list[int]:
        spu_ids = []
        page = 1

        while True:
            status, products = await self._request("GET", "products", params={"per_page": 100, "page": page})
            if not products:
                break
            for product in products:
                spu_id = None
                is_brand_match = False

                # 1. Найти spu_id
                for meta in product.get("meta_data", []):
                    if meta["key"] == "_poizon_spu_id":
                        spu_id = str(meta["value"])

                # 2. Проверить бренд
                for attr in product.get("attributes", []):
                    if attr["name"].lower() == "бренд":
                        if brand.lower() in [v.lower() for v in attr.get("options", [])]:
                            is_brand_match = True
                            break

                if spu_id and is_brand_match:
                    spu_ids.append(meta["value"])
            page += 1

        return spu_ids

    async def delete_product_by_id(self, product_id: int):
        return await self._request("DELETE", f"products/{product_id}", params={"force": 1})

    async def get_product_by_id(self, product_id: int):
        status, product = await self._request("GET", f"products/{product_id}")

        return product if status == 200 and product else None

    async def list_products(self, page: int = 1, per_page: int = 10):
        return await self._request("GET", "products", params={"page": page, "per_page": per_page})

    async def get_all_variations(self, product_id: int) -> list[dict]:
        variations = []
        page = 1

        while True:
            status, page_data = await self._request(
                "GET",
                f"products/{product_id}/variations",
                params={"per_page": 100, "page": page}  # максимум 100
            )
            if not page_data:
                break
            variations.extend(page_data)
            if len(page_data) < 100:
                break
            page += 1

        return variations
