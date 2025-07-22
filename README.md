# Poizon → WooCommerce Sync

Автоматизированный сервис для парсинга товаров с Poizon API и загрузки их в WooCommerce с полной обработкой бизнес-логики.

---

## 📌 Основной функционал

- ✅ **Парсинг Poizon API**  
  Получение данных о товарах (SPU + SKU) с поддержкой постраничной загрузки и лимитов.

- ✅ **Гибкая ценовая политика**  
  - Поддержка нескольких алгоритмов (thepoizon.ru → RUB).
  - Формулы и коэффициенты вынесены в `config.yaml` (без правки кода).

- ✅ **Нормализация брендов**  
  - Автоматическая проверка и создание брендов в WooCommerce.
  - Объединение подбрендов (например, Yeezy → Adidas).
  - Возможность настройки правил через конфиг.

- ✅ **Управление атрибутами и вариациями**  
  - Создание атрибутов (`pa_eu_size`) и терминов через API.
  - Добавление вариативных товаров с размерными опциями.

- ✅ **Slug и SEO-friendly URL**  
  - Автоматическая генерация slug из оригинальной ссылки Poizon.

- ✅ **Модульная архитектура (Onion Architecture)**  
  - **Domain Layer** – бизнес-сущности (SPU, SKU).
  - **Application Layer** – use cases (сценарии) и сервисы (Pricing, BrandNormalizer).
  - **Infrastructure Layer** – клиенты Poizon API, WooCommerce API.
  - **Interface Layer** – CLI / будущий web-интерфейс.

---

## 🏗 Стек технологий
- **Python 3.13+**
- `aiohttp` – асинхронные запросы
- `async-lru` – кэширование
- `PyYAML` – конфиги
- `loguru` – логирование

---

## 📂 Структура проекта

├── domain/ # Чистая бизнес-логика (SPU, SKU) </br>
├── application/</br>
│ ├── use_cases/ # Сценарии: collect_spu, upload_to_woo</br>
│ ├── services/ # PricingService, BrandNormalizer</br>
├── infrastructure/</br>
│ ├── thepoizon_client.py # Работа с The Poizon API</br>
│ ├── woo_client.py # Работа с WooCommerce API</br>
├── config.yaml # Конфигурация </br>
├── main.py # Точка входа (CLI)</br>
└── README.md</br>

---
