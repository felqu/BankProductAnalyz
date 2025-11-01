import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


df = pd.read_csv('result/filtered_bank1.csv',
                 names=['URL', 'grade', 'grade_accepted', 'bank', 'review',
                        'product', 'proxy_used', 'status', 'clear_conditions',
                        'polite_employee', 'availability', 'convience', 'city', 'date'],
                 skiprows=1)

# Предварительный просмотр данных
print("Первые 5 строк:")
print(df.head())
print("\nИнформация о данных:")
print(df.info())
print("\nОсновные статистики:")
print(df.describe())

# 1. Описательная статистика
print("\n" + "=" * 50)
print("ОПИСАТЕЛЬНАЯ СТАТИСТИКА")
print("=" * 50)

# Сводная таблица по категориальным признакам
categorical_columns = ['bank', 'product', 'status', 'city']
for col in categorical_columns:
    print(f"\nРаспределение {col}:")
    print(df[col].value_counts().head(10))

# Сводная таблица по числовым признакам
numeric_columns = ['grade', 'clear_conditions', 'polite_employee', 'availability', 'convience']
print("\nСтатистики числовых признаков:")
print(df[numeric_columns].describe())

# 2. Визуализация распределений
print("\n" + "=" * 50)
print("ВИЗУАЛИЗАЦИЯ РАСПРЕДЕЛЕНИЙ")
print("=" * 50)

# Настройка стиля графиков
plt.style.use('seaborn-v0_8')
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.ravel()

# Распределение числовых признаков
for i, col in enumerate(numeric_columns):
    df[col].hist(bins=20, ax=axes[i], alpha=0.7)
    axes[i].set_title(f'Распределение {col}')
    axes[i].set_xlabel(col)
    axes[i].set_ylabel('Частота')

# Распределение по банкам (топ-10)
top_banks = df['bank'].value_counts().head(10)
axes[5].barh(range(len(top_banks)), top_banks.values)
axes[5].set_yticks(range(len(top_banks)))
axes[5].set_yticklabels(top_banks.index)
axes[5].set_title('Топ-10 банков по количеству отзывов')
axes[5].set_xlabel('Количество отзывов')

plt.tight_layout()
plt.show()

print("\n" + "=" * 50)
print("ВИЗУАЛИЗАЦИЯ ВЫБРОСОВ")
print("=" * 50)

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.ravel()

for i, col in enumerate(numeric_columns):
    df.boxplot(column=col, ax=axes[i])
    axes[i].set_title(f'Выбросы в {col}')


top_5_banks = df['bank'].value_counts().head(5).index
bank_grade_data = df[df['bank'].isin(top_5_banks)]
sns.boxplot(data=bank_grade_data, x='bank', y='grade', ax=axes[5])
axes[5].set_title('Распределение оценок по топ-5 банкам')
axes[5].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.show()


print("\n" + "=" * 50)
print("АНАЛИЗ КОРРЕЛЯЦИЙ")
print("=" * 50)


correlation_matrix = df[numeric_columns].corr()

plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix,
            annot=True,
            cmap='coolwarm',
            center=0,
            square=True,
            fmt='.2f',
            cbar_kws={'shrink': 0.8})
plt.title('Матрица корреляций числовых признаков')
plt.tight_layout()
plt.show()


print("\nДиаграммы рассеяния для пар признаков:")
sns.pairplot(df[numeric_columns],
             diag_kind='hist',
             plot_kws={'alpha': 0.6},
             height=2)
plt.suptitle('Диаграммы рассеяния для числовых признаков', y=1.02)
plt.show()


if 'date' in df.columns:
    try:
        df['date_parsed'] = pd.to_datetime(df['date'], format='%d.%m.%Y %H:%M')
        df['month'] = df['date_parsed'].dt.month
        df['year'] = df['date_parsed'].dt.year

        plt.figure(figsize=(12, 6))
        monthly_reviews = df.groupby(['year', 'month']).size()
        monthly_reviews.plot(kind='line', marker='o')
        plt.title('Динамика количества отзывов по времени')
        plt.xlabel('Дата')
        plt.ylabel('Количество отзывов')
        plt.grid(True)
        plt.show()
    except:
        print("Не удалось проанализировать временные данные")


bool_columns = ['grade_accepted', 'proxy_used']
if bool_columns[0] in df.columns:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for i, col in enumerate(bool_columns):
        df[col].value_counts().plot(kind='bar', ax=axes[i], alpha=0.7)
        axes[i].set_title(f'Распределение {col}')
        axes[i].set_xlabel(col)
        axes[i].set_ylabel('Количество')
    plt.tight_layout()
    plt.show()

print("\n" + "=" * 50)
print("КЛЮЧЕВЫЕ ВЫВОДЫ")
print("=" * 50)
print(f"Общее количество отзывов: {len(df)}")
print(f"Количество уникальных банков: {df['bank'].nunique()}")
print(f"Средняя оценка: {df['grade'].mean():.2f}")
print(f"Распределение оценок:\n{df['grade'].value_counts().sort_index()}")