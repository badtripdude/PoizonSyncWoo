import asyncio
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from loguru import logger

from application.use_cases.collect_spu_from_poizon import collect_spu_from_poizon
from application.use_cases.collect_spus_from_last_top import collect_spus_from_last_top
from application.use_cases.upload_spu_to_woocommerce import upload_all_spus_to_woocommerce
from infrastracture.mappers import SPUMapper
from infrastracture.thepoizon_client import ThePoizonClient
from infrastracture.woo_client import AsyncWooClient

load_dotenv()
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

MAX_PAGES = 10
MAX_PRODUCTS_PER_BRAND = 50

# Настройка логирования в файл
logger.add(
    LOG_DIR / "poizon_sync.log",
    rotation="5 MB",  # автоматическое разделение по размеру
    retention="10 days",  # хранить не более 10 дней
    compression="zip",  # старые логи будут архивироваться
    enqueue=True,  # потокобезопасность для asyncio
    backtrace=True,  # подробный traceback
    diagnose=True,  # выводить переменные при исключении
    level="TRACE"  # уровень логирования
)
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

brands = {
    'Jordan': [13],
    'Nike': [144],
    'Adidas': [3, 10139, 494, 1025980],
    'New Balance': [4],
    'Converse': [176],
    'Vans': [9],
    'Saucony': [10480],
    'Yeezy': [1152, 3, 10139, 494, 1025980],
    'Salomon': [1000079],
}
POIZON_API_KEY = os.getenv("POIZON_API_KEY")


async def main():
    logger.info(f"Запуск...Количество товаров на каждый бренд: {MAX_PRODUCTS_PER_BRAND}. ")
    woo_client = AsyncWooClient(
        url=os.getenv('WC_URL'),
        consumer_key=os.getenv('WC_CONSUMER_KEY'),
        consumer_secret=os.getenv('WC_CONSUMER_SECRET'),
    )
    await woo_client.init_session()
    async with ThePoizonClient(api_key=os.getenv('POIZON_API_KEY')) as pz_client:
        for brand_name, brand_ids in brands.items():
            spus = await collect_spu_from_poizon(brand_name=brand_name,
                                                 brand_ids=brand_ids,
                                                 max_pages=MAX_PAGES,
                                                 max_products=MAX_PRODUCTS_PER_BRAND,
                                                 client=pz_client,
                                                 mapper=SPUMapper,
                                                 )
            old_spus = await collect_spus_from_last_top(new_top=spus,
                                                        woo_client=woo_client,
                                                        pz_client=pz_client,
                                                        brand=brand_name,
                                                        )
            spus.extend(old_spus)

            await upload_all_spus_to_woocommerce(spus=spus,
                                                 client=woo_client,
                                                 config=config,
                                                 mapper=SPUMapper, )
    await woo_client.close()

if __name__ == '__main__':
    asyncio.run(main())
