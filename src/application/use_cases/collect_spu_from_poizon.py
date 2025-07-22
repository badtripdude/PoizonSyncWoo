from loguru import logger

from src.application.services import PoizonSPUService


async def collect_spu_from_poizon(*,
                                  brand_name: str,
                                  brand_ids: list[int],
                                  max_pages: int,
                                  max_products: int,
                                  client, mapper) -> list:
    logger.info(f'Начался поиск по бренду `{brand_name}`...')
    spu_collector = []
    service = PoizonSPUService(client, mapper)

    remaining = max_products
    cur_page = 0

    while cur_page < max_pages and remaining > 0:
        cur_page += 1
        try:
            spus = await service.fetch_page(brand_name=brand_name,
                                            brand_ids=brand_ids,
                                            page=cur_page,
                                            remaining=remaining)
        except Exception as e:
            logger.error(f'Не удалось обработать {brand_name} на странице {cur_page}. msg:{e}')
            break
        spu_collector.extend(spus)
        remaining = max_products - len(spu_collector)
    logger.info(f'По бренду `{brand_name}` обработано {cur_page} страниц и собрано {len(spu_collector)} товаров')
    return spu_collector
