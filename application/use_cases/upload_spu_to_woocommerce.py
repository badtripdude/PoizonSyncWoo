import asyncio

from loguru import logger

import domain
from domain import SPU


async def process_spu(spu, config, mapper, client, ):
    try:
        for sku in spu.skus:
            if sku.regular_price:
                sku.regular_price = await domain.calculate_price(sku.regular_price, mode=config['pricing']['mode'],
                                                                 x=config['pricing']['X'], y=config['pricing']['Y'],
                                                                 z=config['pricing']['Z'])

        base, variations = mapper.from_domain_to_woocomerce(spu)
        status, result = await client.create_or_update_variable_product_with_variations(base, variations)

        if status in [200, 201]:
            logger.success(f"📤 `{spu.title}` успешно выгружен в WooCommerce")
        else:
            logger.error(f"❌ Ошибка выгрузки `{spu.title}`: {result.get('message', result)}")
    except Exception as e:
        logger.error(f"❗ Ошибка при выгрузке `{spu.title}`: {e}")
        logger.exception(e)


async def upload_all_spus_to_woocommerce(*,
                                         spus: list[SPU],
                                         config: dict,
                                         client,
                                         mapper,
                                         ):
    logger.info(f'Началась выгрузка в WooCommerce {len(spus)} товаров')
    for spu in spus:
        await process_spu(spu, config, mapper,client)
    # tasks = [
    #     process_spu(spu, config, mapper, client, )
    #     for spu in spus
    # ]
    # await asyncio.gather(*tasks, return_exceptions=True)
