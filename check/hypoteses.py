import pandas as pd
from scipy.stats import chi2_contingency
from statsmodels.stats.proportion import proportions_ztest
import numpy as np


def check_hypotheses(file_path):

    df = pd.read_csv(file_path)


    required_columns = ['Bank', 'Product', 'sentiment']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Отсутствует обязательный столбец: {col}")


    df = df.dropna(subset=required_columns)


    df['sentiment'] = df['sentiment'].str.upper().str.strip()
    valid_sentiments = {'NEGATIVE', 'NEUTRAL', 'POSITIVE'}
    df = df[df['sentiment'].isin(valid_sentiments)]


    print("Гипотеза 1: Влияние банка на распределение тональности отзывов")
    banks = ['Совкомбанк', 'Альфа-Банк', 'Камкомбанк']
    df_h1 = df[df['Bank'].isin(banks)]
    if df_h1.empty:
        print("Нет данных для указанных банков.")
    else:
        contingency_h1 = pd.crosstab(df_h1['Bank'], df_h1['sentiment'])
        print("Таблица сопряженности:\n", contingency_h1)
        chi2, p, dof, expected = chi2_contingency(contingency_h1)
        print(f"Статистика хи-квадрат: {chi2:.4f}, p-value: {p:.10f}, Степени свободы: {dof}")
        if np.any(expected < 5):
            print("Предупреждение: Некоторые ожидаемые частоты меньше 5. Тест хи-квадрат может быть неточным. Рассмотрите точный тест Фишера.")
        if p < 0.05:
            print("Отвергаем H0: Распределение тональности отличается по крайней мере для одного банка.")
        else:
            print("Не отвергаем H0: Распределение тональности одинаково для всех банков.")

    print("\n" + "-" * 50 + "\n")


    print("Гипотеза 2: Сравнение негативной тональности для ипотеки и дебетовых карт")
    products_h2 = {'ипотека': 'Mortgage', 'дебетовая карта': 'Debit Card'}
    df_h2_mortgage = df[df['Product'] == 'ипотека']
    df_h2_debit = df[df['Product'] == 'дебетовая карта']

    if df_h2_mortgage.empty or df_h2_debit.empty:
        print("Нет данных для ипотеки или дебетовых карт.")
    else:
        neg_mortgage = (df_h2_mortgage['sentiment'] == 'NEGATIVE').sum()
        n_mortgage = len(df_h2_mortgage)
        neg_debit = (df_h2_debit['sentiment'] == 'NEGATIVE').sum()
        n_debit = len(df_h2_debit)

        print(f"Ипотека: Негативные = {neg_mortgage}/{n_mortgage} ({neg_mortgage / n_mortgage:.2%})")
        print(f"Дебетовая карта: Негативные = {neg_debit}/{n_debit} ({neg_debit / n_debit:.2%})")


        z_stat, p_val = proportions_ztest([neg_mortgage, neg_debit], [n_mortgage, n_debit], alternative='larger')
        print(f"Z-статистика: {z_stat:.4f}, p-value: {p_val:.10f}")
        if p_val < 0.05:
            print(
                "Отвергаем H0: Доля негативных отзывов об ипотеке значительно выше, чем о дебетовых картах.")
        else:
            print("Не отвергаем H0: Нет значимой разницы (или не выше для ипотеки).")

    print("\n" + "-" * 50 + "\n")


    print("Гипотеза 3: Связь типа продукта с распределением тональности")
    products_h3 = ['ипотека', 'кредитная карта', 'дебетовая карта', 'вклады']
    df_h3 = df[df['Product'].isin(products_h3)]
    if df_h3.empty:
        print("Нет данных для указанных продуктов.")
    else:
        contingency_h3 = pd.crosstab(df_h3['Product'], df_h3['sentiment'])
        print("Таблица сопряженности:\n", contingency_h3)
        chi2, p, dof, expected = chi2_contingency(contingency_h3)
        print(f"Статистика хи-квадрат: {chi2:.4f}, p-value: {p:.10f}, Степени свободы: {dof}")
        if np.any(expected < 5):
            print("Предупреждение: Некоторые ожидаемые частоты меньше 5. Тест хи-квадрат может быть неточным. Рассмотрите точный тест Фишера.")
        if p < 0.05:
            print("Отвергаем H0: Существует значимая связь между типом продукта и тональностью.")


            residuals = (contingency_h3 - expected) / np.sqrt(expected)
            print("\nСтандартизированные остатки:\n", residuals)
            print("Примечание: Остатки > |1.96| указывают на значимый вклад (при alpha=0.05).")
        else:
            print("Не отвергаем H0: Нет значимой связи между типом продукта и тональностью.")

if __name__=="__main__":


    check_hypotheses('../final dataset/dataset_with_sentiment2.csv')