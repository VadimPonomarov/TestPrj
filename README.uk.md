# Сервіс збору даних про товари Brain

Це Django-проєкт, який парсить картки товарів на **brain.com.ua**, зберігає
нормалізовані дані в PostgreSQL і надає REST API для отримання переліку товарів
та експорту у CSV.

## Попередні вимоги

- Docker і Docker Compose
- Python 3.11 та Poetry
- Доступ до цільових URL на brain.com.ua

## Швидкий старт

1. Встановіть Python-залежності:

   ```bash
   poetry install
   ```

2. Запустіть PostgreSQL через Docker Compose:

   ```bash
   docker-compose up -d db
   ```

3. Застосуйте міграції (параметри беруться з `.env`):

   ```bash
   poetry run python manage.py migrate
   ```

4. Спарсьте та збережіть товар (приклад через shell):

   ```bash
   poetry run python manage.py shell -c "from parser_app.services.brain_parser import BrainProductParser; from parser_app.models import Product; url='https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_Pro_Max_512GB_White_Titanium-p1044402.html'; data=BrainProductParser(url).parse(); code=data.pop('product_code'); Product.objects.update_or_create(product_code=code, defaults=data)"
   ```

5. Запустіть API локально:

   ```bash
   poetry run python manage.py runserver 0.0.0.0:8000
   ```

## API-ендпоінти

Базовий шлях: `/api/`

| Метод | Шлях                      | Опис                                       |
| ----- | ------------------------- | ------------------------------------------ |
| POST  | `/products/scrape/`       | Спарсити товар Brain та оновити/додати його |
| GET   | `/products/`              | Сторінковий список товарів                 |
| POST  | `/products/`              | Додати товар вручну                        |
| GET   | `/products/<id>/`         | Отримати товар за ID                       |
| GET   | `/products/export-csv/`   | Завантажити CSV з усіма товарами           |

### Експорт у CSV

CSV містить усі поля серіалізатора. Складні структури (`images`, `metadata`,
`characteristics`) серіалізуються у JSON-рядки. Приклад:

```bash
curl -H "Host: localhost" http://127.0.0.1:8000/api/products/export-csv/ -o temp/products.csv
```

## Пряме використання парсера

```python
from parser_app.services.brain_parser import BrainProductParser, format_product_output

parser = BrainProductParser("https://brain.com.ua/ukr/product-url.html")
data = parser.parse()

print(format_product_output(data))
```

Парсер повертає словник з полями:
- `name`, `product_code`, `price`, `sale_price`
- `manufacturer`, `color`, `storage`
- `review_count`, `screen_diagonal`, `display_resolution`
- `images` (список URL)
- `characteristics` (словник)
- `metadata` (оригінальні дані JSON-LD)

Детальна логіка описана у `parser_app/README.md`.
