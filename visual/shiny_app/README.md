# Дашборд

Интерактивное приложение на Shiny for Python для исследования отзывов,
собранных в `../../final dataset/dataset_with_sentiment2.csv`.

Запуск из корня репозитория:

```bash
pip install -r visual/shiny_app/requirements.txt
shiny run --reload visual/shiny_app/app.py
```

Приложение поддерживает фильтрацию по банку, продукту, городу, тональности и
времени; выводит распределения оценок, динамику отзывов и показатели
тональности.
