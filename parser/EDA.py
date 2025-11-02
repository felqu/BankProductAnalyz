import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

import warnings

warnings.filterwarnings('ignore')

# Настройка стиля для лучшей визуализации
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)

df = pd.read_csv('result/filtered_bank1.csv',
                 names=['URL', 'grade', 'grade_accepted', 'bank', 'review',
                        'product', 'proxy_used', 'status', 'clear_conditions',
                        'polite_employee', 'availability', 'convience', 'city', 'date'],
                 skiprows=1)
pd.set_option('display.width', 1000)
pd.set_option('display.max_columns', None)

print("Первые 5 строк:")
print(df.head())
print("\nИнформация о данных:")
print(df.info())
print("\nОсновные статистики:")
print(df.describe())


print("\n" + "=" * 50)
print("АНАЛИЗ ПРОПУЩЕННЫХ ЗНАЧЕНИЙ")
print("=" * 50)
missing_data = df.isnull().sum()
missing_percent = (df.isnull().sum() / len(df)) * 100
missing_info = pd.DataFrame({
    'Количество пропусков': missing_data,
    'Процент пропусков': missing_percent
})
print(missing_info[missing_info['Количество пропусков'] > 0])


print("\n" + "=" * 50)
print("ОПИСАТЕЛЬНАЯ СТАТИСТИКА")
print("=" * 50)


categorical_columns = ['bank', 'product', 'status', 'city']
for col in categorical_columns:
    print(f"\nРаспределение {col}:")
    value_counts = df[col].value_counts()
    print(f"Всего уникальных значений: {len(value_counts)}")
    print(value_counts.head(10))
    if len(value_counts) > 10:
        print(f"... и еще {len(value_counts) - 10} других значений")

print("\nАнализ булевых признаков:")
bool_columns = ['grade_accepted', 'proxy_used']
for col in bool_columns:
    if col in df.columns:
        print(f"\n{col}:")
        print(df[col].value_counts(normalize=True).map(lambda x: f"{x:.1%}"))

print("\n" + "=" * 50)
print("АНАЛИЗ ОЦЕНОК")
print("=" * 50)

numeric_columns = ['grade', 'clear_conditions', 'polite_employee', 'availability', 'convience']

print("Детальная статистика оценок:")
for col in numeric_columns:
    print(f"\n{col}:")
    print(f"  Медиана: {df[col].median():.2f}")
    print(f"  Мода: {df[col].mode().iloc[0] if not df[col].mode().empty else 'N/A'}")
    print(f"  Стандартное отклонение: {df[col].std():.2f}")
    print(f"  Диапазон: {df[col].min()} - {df[col].max()}")

print("\n" + "=" * 50)
print("ВИЗУАЛИЗАЦИЯ РАСПРЕДЕЛЕНИЙ")
print("=" * 50)

fig, axes = plt.subplots(3, 3, figsize=(18, 15))
axes = axes.ravel()

for i, col in enumerate(numeric_columns[:5]):
    df[col].hist(bins=20, ax=axes[i], alpha=0.7, color='skyblue', edgecolor='black')
    axes[i].axvline(df[col].mean(), color='red', linestyle='--', label=f'Среднее: {df[col].mean():.2f}')
    axes[i].axvline(df[col].median(), color='green', linestyle='--', label=f'Медиана: {df[col].median():.2f}')
    axes[i].set_title(f'Распределение {col}', fontsize=12, fontweight='bold')
    axes[i].set_xlabel('Оценка')
    axes[i].set_ylabel('Частота')
    axes[i].legend()

top_banks = df['bank'].value_counts().head(10)
axes[5].barh(range(len(top_banks)), top_banks.values, color='lightcoral')
axes[5].set_yticks(range(len(top_banks)))
axes[5].set_yticklabels(top_banks.index)
axes[5].set_title('Топ-10 банков по количеству отзывов', fontsize=12, fontweight='bold')
axes[5].set_xlabel('Количество отзывов')

plt.figure(figsize=(10, 8))
top_products = df['product'].value_counts().head(8)

plt.pie(top_products.values,
        labels=top_products.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=plt.cm.Set3(np.linspace(0, 1, len(top_products))),
        textprops={'fontsize': 12})

plt.title('Распределение отзывов по банковским продуктам (топ-8)',
          fontsize=16, fontweight='bold', pad=20)
plt.axis('equal')  # Обеспечиваем круглую форму

# Добавляем легенду для лучшей читаемости
plt.legend(top_products.index,
           title="Типы продуктов",
           loc="center left",
           bbox_to_anchor=(1, 0, 0.5, 1))

plt.tight_layout()
plt.show()

print("\n" + "="*60)
print("АНАЛИЗ РАСПРЕДЕЛЕНИЯ ОТЗЫВОВ ПО ПРОДУКТАМ")
print("="*60)
print(f"Всего уникальных типов продуктов: {df['product'].nunique()}")
print(f"Топ-8 продуктов охватывает {top_products.sum()} отзывов "
      f"({top_products.sum()/len(df)*100:.1f}% от общего количества)")

print("\nДетальное распределение по топ-8 продуктам:")
for i, (product, count) in enumerate(top_products.items(), 1):
    percentage = (count / len(df)) * 100
    print(f"{i:2d}. {product:<25} {count:>4} отзывов ({percentage:5.1f}%)")

other_products = df['product'].value_counts().iloc[8:]
if len(other_products) > 0:
    other_count = other_products.sum()
    print(f"\nОстальные продукты ({len(other_products)} видов): "
          f"{other_count} отзывов ({other_count/len(df)*100:.1f}%)")

status_counts = df['status'].value_counts()
axes[7].bar(range(len(status_counts)), status_counts.values, color='lightgreen', alpha=0.7)
axes[7].set_xticks(range(len(status_counts)))
axes[7].set_xticklabels(status_counts.index, rotation=45)
axes[7].set_title('Распределение по статусам', fontsize=12, fontweight='bold')
axes[7].set_ylabel('Количество')

# Оставляем последний subplot пустым
axes[8].axis('off')

plt.tight_layout()
plt.show()

# 4. Анализ выбросов
print("\n" + "=" * 50)
print("АНАЛИЗ ВЫБРОСОВ")
print("=" * 50)

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
axes = axes.ravel()




top_5_banks = df['bank'].value_counts().head(5).index
bank_grade_data = df[df['bank'].isin(top_5_banks)]
sns.boxplot(data=bank_grade_data, x='bank', y='grade', ax=axes[5])
axes[5].set_title('Распределение оценок по топ-5 банкам', fontsize=12, fontweight='bold')
axes[5].tick_params(axis='x', rotation=45)
axes[5].set_xlabel('Банк')
axes[5].set_ylabel('Общая оценка')

plt.tight_layout()
plt.show()


print("\n" + "=" * 50)
print("АНАЛИЗ КОРРЕЛЯЦИЙ")
print("=" * 50)

correlation_matrix = df[numeric_columns].corr()


plt.figure(figsize=(12, 10))
mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
sns.heatmap(correlation_matrix,
            annot=True,
            cmap='RdYlBu',
            center=0,
            square=True,
            fmt='.3f',
            cbar_kws={'shrink': 0.8},
            mask=mask,
            annot_kws={'size': 12})
plt.title('Матрица корреляций числовых признаков\n(треугольная маска)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()

high_corr_pairs = []
for i in range(len(correlation_matrix.columns)):
    for j in range(i + 1, len(correlation_matrix.columns)):
        if abs(correlation_matrix.iloc[i, j]) > 0.5:  # Порог корреляции
            high_corr_pairs.append((
                correlation_matrix.columns[i],
                correlation_matrix.columns[j],
                correlation_matrix.iloc[i, j]
            ))

if high_corr_pairs:
    print("\nНаиболее коррелированные пары признаков (|r| > 0.5):")
    for col1, col2, corr in high_corr_pairs:
        print(f"  {col1} - {col2}: {corr:.3f}")


print("\n" + "=" * 50)
print("АНАЛИЗ ПО БАНКАМ И ПРОДУКТАМ")
print("=" * 50)

print("\nСредние оценки по банкам (топ-10 по количеству отзывов):")
top_banks_stats = df[df['bank'].isin(top_banks.index)].groupby('bank')[numeric_columns].mean()
top_banks_stats['count'] = df[df['bank'].isin(top_banks.index)]['bank'].value_counts()
print(top_banks_stats.sort_values('count', ascending=False))

plt.figure(figsize=(14, 8))
bank_scores = df.groupby('bank')[numeric_columns].mean()
min_reviews = 5
bank_counts = df['bank'].value_counts()
qualified_banks = bank_counts[bank_counts >= min_reviews].index
bank_scores_filtered = bank_scores.loc[qualified_banks]


bank_scores_filtered = bank_scores_filtered.sort_values('grade', ascending=False).head(15)

bank_scores_filtered.plot(kind='bar', width=0.8)
plt.title(f'Средние оценки по банкам (минимум {min_reviews} отзывов)', fontsize=14, fontweight='bold')
plt.xlabel('Банк')
plt.ylabel('Средняя оценка')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


if 'date' in df.columns:
    print("\n" + "=" * 50)
    print("ВРЕМЕННОЙ АНАЛИЗ")
    print("=" * 50)

    try:
        df['date_parsed'] = pd.to_datetime(df['date'], format='%d.%m.%Y %H:%M', errors='coerce')
        df['month'] = df['date_parsed'].dt.to_period('M')
        df['year'] = df['date_parsed'].dt.year

        # Анализ временного тренда
        plt.figure(figsize=(15, 10))

        # Количество отзывов по месяцам
        plt.subplot(2, 2, 1)
        monthly_reviews = df.groupby('month').size()
        monthly_reviews.plot(kind='line', marker='o', color='blue')
        plt.title('Динамика количества отзывов по месяцам')
        plt.xlabel('Месяц')
        plt.ylabel('Количество отзывов')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)

        # Средняя оценка по месяцам
        plt.subplot(2, 2, 2)
        monthly_grade = df.groupby('month')['grade'].mean()
        monthly_grade.plot(kind='line', marker='s', color='red')
        plt.title('Динамика средней оценки по месяцам')
        plt.xlabel('Месяц')
        plt.ylabel('Средняя оценка')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)

        # Распределение отзывов по дням недели
        plt.subplot(2, 2, 3)
        df['day_of_week'] = df['date_parsed'].dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_counts = df['day_of_week'].value_counts().reindex(day_order)
        day_counts.plot(kind='bar', color='green', alpha=0.7)
        plt.title('Распределение отзывов по дням недели')
        plt.xlabel('День недели')
        plt.ylabel('Количество отзывов')
        plt.xticks(rotation=45)

        # Распределение по часам
        plt.subplot(2, 2, 4)
        df['hour'] = df['date_parsed'].dt.hour
        hour_counts = df['hour'].value_counts().sort_index()
        hour_counts.plot(kind='bar', color='orange', alpha=0.7)
        plt.title('Распределение отзывов по часам дня')
        plt.xlabel('Час')
        plt.ylabel('Количество отзывов')

        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"Ошибка при анализе временных данных: {e}")

# 8. Географический анализ
print("\n" + "=" * 50)
print("ГЕОГРАФИЧЕСКИЙ АНАЛИЗ")
print("=" * 50)

if 'city' in df.columns:
    print("Топ-15 городов по количеству отзывов:")
    top_cities = df['city'].value_counts().head(15)
    print(top_cities)

    plt.figure(figsize=(12, 8))
    top_cities.plot(kind='barh', color='lightseagreen')
    plt.title('Топ-15 городов по количеству отзывов', fontsize=14, fontweight='bold')
    plt.xlabel('Количество отзывов')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.show()

print("\n" + "=" * 50)
print("ДЕТАЛЬНЫЙ АНАЛИЗ ОЦЕНОК ПО КАТЕГОРИЯМ")
print("=" * 50)

if 'product' in df.columns:
    product_analysis = df.groupby('product')[numeric_columns].agg(['mean', 'count', 'std'])
    print("\nСтатистика оценок по типам продуктов:")
    print(product_analysis)

# 10. Ключевые выводы
print("\n" + "=" * 50)
print("КЛЮЧЕВЫЕ ВЫВОДЫ")
print("=" * 50)

print(f"Общее количество отзывов: {len(df):,}")
print(f"Количество уникальных банков: {df['bank'].nunique()}")
print(f"Количество уникальных продуктов: {df['product'].nunique()}")
print(f"Количество уникальных городов: {df['city'].nunique()}")
print(f"\nСредняя оценка: {df['grade'].mean():.2f}")
print(f"Медианная оценка: {df['grade'].median():.2f}")

print(f"\nРаспределение общих оценок:")
grade_dist = df['grade'].value_counts().sort_index()
for grade, count in grade_dist.items():
    percentage = (count / len(df)) * 100
    print(f"  Оценка {grade}: {count} отзывов ({percentage:.1f}%)")


high_grades = len(df[df['grade'] >= 4])
low_grades = len(df[df['grade'] <= 2])
medium_grades = len(df[(df['grade'] > 2) & (df['grade'] < 4)])

print(f"\nУровень удовлетворенности:")
print(f"  Высокие оценки (4-5): {high_grades} ({high_grades / len(df) * 100:.1f}%)")
print(f"  Средние оценки (3): {medium_grades} ({medium_grades / len(df) * 100:.1f}%)")
print(f"  Низкие оценки (1-2): {low_grades} ({low_grades / len(df) * 100:.1f}%)")

# Самые популярные банки
print(f"\nТоп-5 банков по количеству отзывов:")
for i, (bank, count) in enumerate(df['bank'].value_counts().head(5).items(), 1):
    print(f"  {i}. {bank}: {count} отзывов")

print(f"\nТоп-5 продуктов по количеству отзывов:")
for i, (product, count) in enumerate(df['product'].value_counts().head(5).items(), 1):
    print(f"  {i}. {product}: {count} отзывов")