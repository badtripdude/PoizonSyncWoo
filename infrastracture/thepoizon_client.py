import asyncio

from aiohttp import ClientSession, ClientResponseError
from loguru import logger

from application.interfaces import PoizonClient

'''
categoryIds:
29 - туфля
1005116 - Кроссовки для бега,
38 - кроссовки
35 - Модная повседневная обувь

30 - кроссовки
33 - кроссовки
31 - кроссовки
32 - Футбольная обувь
34 - Тренировочная обувь
1003478 - Походная обувь/ботинки для пешего туризма
1000266 - Модная обувь
1001189 - Повседневная обувь для жизни
1001176 - Баскетбольные туфли в стиле ретро
1005402 - Повседневная кожаная обувь
1004168 - Спортивная обувь
1005501 - Обувь для ходьбы
1005113 - Обувь для занятий фитнесом в помещении


fitIds:
1 - Унисекс
2 - Мужчины
3 - Женщины

SortType:
1 - Топ Продаж
0 - Рекомендуемые
3 - Новые
4 - Цена
'''


# class PoizonSPU(DewuProduct):
#     ...


class ThePoizonClient(PoizonClient):
    def __init__(self,
                 api_key: str,
                 base_url: str = "https://poizon-api.com/api/poizon-ru/",
                 sleep_sec: float = 0.5,
                 ):
        self.api_key = api_key
        self.base_url = base_url
        self.sleep_sec = sleep_sec
        self.session: ClientSession | None = None

    async def __aenter__(self):
        self.session = ClientSession(
            base_url=self.base_url,
            headers={"x-api-key": self.api_key}
        )
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def search_products(self, keyword: str,
                              page: int = 1,
                              page_size: int = 20,
                              category_ids: list = None,
                              fit_ids: list = None) -> list[dict]:
        if category_ids is None:  # shoes
            category_ids = [29, 1005116, 38, 35, 30, 33, 31, 32, 34, 1003478, 1000266, 1001189, 1001176,
                            1005402,
                            1004168, 1005501, 1005113]
        if fit_ids is None:  # Men Women Uni
            fit_ids = [1, 2, 3]
        try:
            res = await self.session.get("poizon-api/search", params={
                "keyword": keyword,
                "page": page,
                "pageSize": page_size,
                "fitIds": fit_ids,
                'categoryIds': category_ids,
                "sortType": 1
            })
            data = await res.json()
            if res.status != 200:
                raise Exception(f"Ошибка поиска товаров на странице: {data.get('msg', data)}")
            return data.get("searchSpuList", {}).get("spuList", [])
        except ClientResponseError as e:
            logger.error(f"Ошибка поиска товаров на странице {page}: {e}")
            return []

    async def get_product_info(self, spu_id: str) -> dict:
        try:
            res = await self.session.get(f"poizon-api/product-info/{spu_id}")

            data = await res.json()

            if res.status != 200:
                raise Exception(data)
            await asyncio.sleep(self.sleep_sec)
            return data
        except ClientResponseError as e:
            logger.error(f"Ошибка получения информации о товаре {spu_id}: {e}")
            return {}
