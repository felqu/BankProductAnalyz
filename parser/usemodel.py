import numpy as np
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from scipy.special import softmax


model_name = "blanchefort/rubert-base-cased-sentiment"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)



def predict_sentiment(text):
    # Кодируем текст
    inputs = tokenizer(
        text,
        max_length=512,
        padding=True,
        truncation=True,
        return_tensors='pt'
    )

    # Предикт
    with torch.no_grad():
        outputs = model(**inputs)

    # Применяем softmax для получения вероятностей
    probs = softmax(outputs.logits.numpy(), axis=1)

    # Получаем метки классов из конфигурации модели
    id2label = model.config.id2label
    predictions = {id2label[i]: float(probs[0][i]) for i in range(len(id2label))}

    return predictions



df = pd.read_csv('result/dataset.csv')


results = df['Review'].apply(predict_sentiment).apply(pd.Series)

output_df = pd.concat([df, results], axis=1)

# Сохраняем результат
output_df.to_csv('output2_with_sentiment.csv', index=False, encoding='utf-8-sig')

df = pd.read_csv("output2_with_sentiment.csv")

tolerance = 0.001  # точность ±0.001
filtered_df = df[np.isclose(df['NEGATIVE'], 0.751, atol=tolerance)]


def get_sentiment(row):
    max_value = max(row['NEGATIVE'], row['POSITIVE'], row['NEUTRAL'])

    # Проверяем порог 0.75
    if max_value < 0.75:
        return 'untraced'  # или другое значение по умолчанию

    # Определяем sentiment по максимальному значению
    if max_value == row['POSITIVE']:
        return 'POSITIVE'
    elif max_value == row['NEGATIVE']:
        return 'NEGATIVE'
    else:
        return 'NEUTRAL'


# Добавляем столбец
df['sentiment'] = df.apply(get_sentiment, axis=1)
# Более читаемый способ с query
df = df.query('not ((Grade == 5 or Grade == 4) and sentiment == "NEGATIVE")')
df = df.query('not (sentiment == "untraced")')

df.to_csv('dataset_with_sentiment2.csv', index=False)