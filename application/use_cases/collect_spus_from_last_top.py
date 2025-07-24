import asyncio

from loguru import logger
from application.services import PoizonSPUService
from infrastracture import mappers
from utils import retry_async


async def collect_spus_from_last_top(*,
                                     new_top: list,
                                     woo_client,
                                     pz_client,
                                     brand: str) -> list:
    """
    Собирает товары из предыдущей выгрузки, которые есть в WooCommerce,
    но не входят в новый топ.

    :param new_top: Список SPU из нового топа
    :param woo_client: экземпляр клиента WooCommerce
    :param pz_client: экземпляр клиента Poizon
    :param brand: бренд для фильтрации
    :return: список SPU (старые, вышедшие из топа)
    """
    logger.info(f'Начался сбор товаров из предыдущего топа по бренду `{brand}` ...')
    pz_service = PoizonSPUService(client=pz_client,
                                  mapper=mappers.SPUMapper)
    # Получаем ID SPU из нового топа
    new_spu_ids = {spu.id_ for spu in new_top}

    # Получаем все товары WooCommerce для бренда
    existing_products = await woo_client.get_all_products_by_brand(brand=brand)

    old_spus = []
    for product in existing_products:
        try:
            # Проверяем meta_data на наличие _poizon_spu_id
            spu_id_meta = next((meta["value"] for meta in product.get("meta_data", [])
                                if meta["key"] == "_poizon_spu_id"), None)
            if spu_id_meta and int(spu_id_meta) not in new_spu_ids:
                spu_id_meta = int(spu_id_meta)
                old_spu = await pz_service.get_spu_by_spu_id(spu_id=spu_id_meta)
                await asyncio.sleep(0.6)
                if old_spu.skus and old_spu.article_code:
                    logger.info(
                        f'Добавлен товар для обновления из прошлого топа `{old_spu.title}`(id={old_spu.id_}) with category={old_spu.category_id}, skus={len(old_spu.skus)}; '
                        f'images={len(old_spu.images)}')
                    old_spus.append(old_spu)
        except Exception as e:
            logger.warning(f"Ошибка загрузки SPU {product}: {e}")
    logger.info(
        f'Собрано {len(existing_products)} товаров из прошлого топа. Из них не попали в новый топ и подлежат обновлению {len(old_spus)} товаров...')
    return old_spus
