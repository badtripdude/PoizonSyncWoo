import asyncio
import re
from urllib.parse import urlparse

from loguru import logger


def extract_slug(url: str) -> str:
    """
    Извлекает slug из ссылки thepoizon.ru/product/...
    """
    parsed = urlparse(url)
    # Разбиваем путь и берем последнюю часть
    path_parts = parsed.path.strip("/").split("/")
    if "product" in path_parts:
        index = path_parts.index("product")
        if index + 1 < len(path_parts):
            return path_parts[index + 1]
    return ""


async def retry_async(
        func,
        *args,
        retries: int = 3,
        delay: float = 1.0,
        allowed_exceptions: tuple = (Exception,),
        **kwargs
):
    attempt = 0
    while attempt < retries:
        try:
            return await func(*args, **kwargs)
        except allowed_exceptions as e:
            attempt += 1
            logger.warning(f"[retry_async] Ошибка при вызове {func.__name__}: {e}. Попытка {attempt}/{retries}")
            if attempt >= retries:
                logger.error(f"[retry_async] Все {retries} попытки исчерпаны.")
                raise e
            await asyncio.sleep(delay)


def is_url(string):
    # Простое регулярное выражение для проверки URL
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// или https://
        r'(?:\S+(?::\S*)?@)?'  # опциональные имя пользователя и пароль
        r'(?:\S+\.)+[a-z]{2,}'  # домен...
        r'(?::\d{2,5})?'  # опциональный порт
        r'(?:/\S*)?$',  # остальная часть URL
        re.IGNORECASE)

    return re.match(regex, string) is not None


def remove_chinese_characters(text: str) -> str:
    # Китайские символы находятся в диапазонах Юникода
    # chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+')
    chinese_and_junk_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303F\uFF00-\uFFEF]+')
    return chinese_and_junk_pattern.sub('', text)


VARIANT_KEYS_TRANSLATION = {
    "尺码": "size",
    "颜色": "color",
    "材质": "material",
    "鞋帮高度": "cut",
    "适用季节": "season",
    "适用性别": "gender",
    # ...
}

# 🌐 Словарь трансляции значений (китайский → английский)
VARIANT_VALUES_TRANSLATION = {
    "黑白": "black & white",
    "白黑": "white & black",
    "白": "white",
    "黑": "black",
    "男": "male",
    "女": "female",
    "春季": "spring",
    "秋季": "autumn",
    "夏季": "summer",
    "冬季": "winter",
    "白黑（材质升级款）": "white & black (upgraded material)",
    "粉色": "pink",
    # ...
}


def normalize_variants(raw_variants: dict[str, str]) -> dict[str, str]:
    """
    Преобразует словарь с вариантами SKU из формата API
    в нормализованный словарь с ключами и значениями на английском языке.
    """
    normalized = {}
    for raw_key, raw_value in raw_variants.items():
        key = VARIANT_KEYS_TRANSLATION.get(raw_key.strip(), raw_key.strip())
        value = VARIANT_VALUES_TRANSLATION.get(raw_value.strip(), raw_value.strip())
        normalized[key] = value
    return normalized


def is_likely_kids_product(title: str) -> bool:
    """
    Возвращает True, если товар скорее всего детская обувь.
    """
    title = title.lower()

    kids_keywords = ["童鞋", "小童", "大童", "儿童", "婴", "学步鞋", "kids", "儿童款", "child", "children", "baby",
                     "youth"]

    if any(kw in title for kw in kids_keywords):
        return True

    # if price < 400:
    #     return True

    # if sizes and all(float(s.replace("EU", "").strip()) < 36 for s in sizes if "EU" in s):
    #     return True

    return False
