import asyncio

from loguru import logger

from domain import SPU
from utils import retry_async


class PoizonSPUService:
    def __init__(self, client, mapper):
        self.client = client
        self.mapper = mapper

    async def fetch_page(self, *,
                         brand_name: str, brand_ids: list[int],
                         page: int, remaining: int) -> list[SPU]:
        products = await retry_async(self.client.search_products, brand_name, page, page_size=20,
                                     retries=5,
                                     delay=5)
        spus = []
        for product in products:
            if product.get('brandId') not in brand_ids:
                logger.debug(
                    f"Товар `{product.get('title')}` не соответствует бренду `{brand_name}(id = {brand_ids})`. "
                    f"Найденный бренд id = {product.get('brandId')}. Ищем дальше...")
                continue

            if 'adidas' in brand_name.lower() and 'yeezy' in product.get('title').lower():
                logger.debug(f"При парсинге бренда Adidas найден товар `{product.get('title')}`. Пропускаем...")
                continue
            if remaining <= 0:
                break
            spu = await self.get_spu_by_spu_id(product['spuId'])
            if spu.skus and spu.article_code:
                spus.append(spu)
                remaining -= 1
                logger.info(
                    f'Получен товар `{spu.title}`(id={spu.id_}) with category={spu.category_id}, skus={len(spu.skus)}; '
                    f'images={len(spu.images)}')
                await asyncio.sleep(1)
            else:
                logger.warning(f"Пропускаем `{spu.title}` — нет размеров или артикула")
        return spus

    async def get_spu_by_spu_id(self, spu_id:int) -> SPU:
        detailed_product = await retry_async(self.client.get_product_info, spu_id,
                                             retries=5,
                                             delay=1)
        spu = self.mapper.from_poizon_to_domain(detailed_product)
        return spu




class BrandNormalizer:
    BRAND_MAP = {
        "adidas": ["adidas terrex", "adidas", "adidas neo", "adidas originals", "adidas yeezy"],
        "new balance": ["nb", "new balance"],

    }
    SPECIAL_RULES = {
        "YEEZY": ["yeezy"]  # проверка по названию
    }

    @staticmethod
    def normalize_brand(*, raw_brand: str, title: str) -> str:
        """
        Нормализует бренд по правилам:
        1. Если в названии есть ключевое слово (YEEZY) — возвращаем YEEZY.
        2. Иначе используем BRAND_MAP.
        """
        title_lower = title.lower()
        # Проверяем спецправила по названию
        for special_brand, keywords in BrandNormalizer.SPECIAL_RULES.items():
            if any(keyword in title_lower for keyword in keywords):
                return special_brand

        lower_brand = raw_brand.lower()
        for normalized, aliases in BrandNormalizer.BRAND_MAP.items():
            if lower_brand in aliases:
                return normalized
        return raw_brand


class BrandFilterService:
    EXCLUDE_RULES = {
        "adidas": ["yeezy"],
        "adidas originals": ["yeezy"],
        "adidas terrex": ["yeezy"],
        "adidas neo": ["yeezy"],
    }

    @staticmethod
    def should_skip(parent_brand: str, sub_brand: str) -> bool:
        sub_brand_lower = sub_brand.lower()
        parent_brand_lower = parent_brand.lower()
        return sub_brand_lower in BrandFilterService.EXCLUDE_RULES.get(parent_brand_lower, [])
