import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


df = pd.read_csv('../final dataset/dataset_with_sentiment2.csv')


df['max_confidence'] = df[['NEGATIVE', 'NEUTRAL', 'POSITIVE']].max(axis=1)


confidence_stats = {
    'total_reviews': len(df),
    'confidence_above_08': len(df[df['max_confidence'] >= 0.8]),
    'confidence_above_075': len(df[df['max_confidence'] >= 0.75]),
    'mean_confidence': df['max_confidence'].mean(),
    'median_confidence': df['max_confidence'].median()
}


confidence_stats['percent_above_08'] = (confidence_stats['confidence_above_08'] / confidence_stats['total_reviews']) * 100
confidence_stats['percent_above_075'] = (confidence_stats['confidence_above_075'] / confidence_stats['total_reviews']) * 100

print("=== АНАЛИЗ УВЕРЕННОСТИ МОДЕЛИ ===")
print(f"Всего отзывов: {confidence_stats['total_reviews']}")
print(f"Отзывов с уверенностью ≥ 0.8: {confidence_stats['confidence_above_08']} ({confidence_stats['percent_above_08']:.1f}%)")
print(f"Отзывов с уверенностью ≥ 0.75: {confidence_stats['confidence_above_075']} ({confidence_stats['percent_above_075']:.1f}%)")
print(f"Средняя уверенность: {confidence_stats['mean_confidence']:.3f}")
print(f"Медианная уверенность: {confidence_stats['median_confidence']:.3f}")


bins = [0, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0]
distribution = pd.cut(df['max_confidence'], bins=bins).value_counts().sort_index()

print("\n=== ДЕТАЛЬНОЕ РАСПРЕДЕЛЕНИЕ ===")
for range_bin, count in distribution.items():
    percent = (count / len(df)) * 100
    print(f"{range_bin}: {count} отзывов ({percent:.1f}%)")


plt.figure(figsize=(10, 6))
plt.hist(df['max_confidence'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
plt.axvline(0.8, color='red', linestyle='--', label='Порог 0.8')
plt.axvline(0.75, color='orange', linestyle='--', label='Порог 0.75')
plt.xlabel('Уверенность модели')
plt.ylabel('Количество отзывов')
plt.title('Распределение уверенности модели')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('confidence_distribution.png', dpi=300, bbox_inches='tight')
plt.show()