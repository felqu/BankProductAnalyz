import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import pandas as pd
import re


# ==================== CONFIG ====================
class Config:
    MODEL_PATH = "./bert_sentiment_model"  # Путь к вашей обученной модели
    MAX_LENGTH = 256


config = Config()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ==================== ЗАГРУЗКА МОДЕЛИ ====================

def load_trained_model(model_path):
    """Загрузка обученной модели и токенизатора"""
    print("Загрузка модели...")

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        model.to(device)
        model.eval()

        print("✅ Модель успешно загружена!")
        return tokenizer, model
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        return None, None


# ==================== ФУНКЦИЯ ПРЕДСКАЗАНИЯ ====================

def predict_sentiment(texts, model, tokenizer, device):
    """Предсказание тональности для списка текстов"""

    # Определяем названия классов на основе количества меток в модели
    num_labels = model.config.num_labels
    if num_labels == 3:
        label_map = {0: "Негативный", 1: "Нейтральный", 2: "Позитивный"}
    elif num_labels == 2:
        label_map = {0: "Негативный", 1: "Позитивный"}
    else:
        label_map = {i: f"Класс_{i}" for i in range(num_labels)}

    predictions = []
    confidence_scores = []
    all_probs = []

    for text in texts:
        # Очистка текста
        cleaned_text = re.sub(r'http\S+', '', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip().lower()

        # Токенизация
        inputs = tokenizer(
            cleaned_text,
            add_special_tokens=True,
            max_length=config.MAX_LENGTH,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Предсказание
        with torch.no_grad():
            outputs = model(**inputs)

        # Вероятности
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        pred_class = torch.argmax(probs, dim=1).cpu().numpy()[0]
        confidence = torch.max(probs).cpu().numpy()
        probabilities = probs.cpu().numpy()[0]

        predictions.append(label_map[pred_class])
        confidence_scores.append(confidence)
        all_probs.append(probabilities)

    return predictions, confidence_scores, all_probs, label_map


# ==================== ТЕСТИРОВАНИЕ ====================

def test_model():
    """Тестирование модели на различных примерах"""

    # Загрузка модели
    tokenizer, model = load_trained_model(config.MODEL_PATH)
    if model is None:
        return

    # Тестовые примеры (можете изменить на свои)
    test_texts = [
        # Позитивные отзывы
        "Очень доволен обслуживанием! Быстро и качественно оформили кредит.",
        "Спасибо сотрудникам банка за профессиональный подход и вежливость.",
        "Отличный банк, удобное мобильное приложение, всегда помогают.",

        # Негативные отзывы
        "Ужасный сервис, долго ждал в очереди, сотрудники грубые.",
        "Никогда больше не обращусь в этот банк, постоянно проблемы.",
        "Очень разочарован, не рекомендую этот банк никому.",

        # Нейтральные отзывы
        "Все нормально, без особых эмоций. Обычный банк как все.",
        "Обслуживание стандартное, ничего особенного не заметил.",
        "В целом нормально, но есть куда расти.",

        # Сложные случаи
        "С одной стороны, вежливые сотрудники, но с другой - очень долгие процедуры.",
        "Приложение удобное, но часто вылетает и глючит.",
        "Первоначально были проблемы, но потом все исправили и теперь нормально."
    ]

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ МОДЕЛИ НА РАЗЛИЧНЫХ ПРИМЕРАХ")
    print("=" * 60)

    # Предсказание
    predictions, confidences, probabilities, label_map = predict_sentiment(
        test_texts, model, tokenizer, device
    )

    # Вывод результатов
    for i, (text, pred, conf, probs) in enumerate(zip(test_texts, predictions, confidences, probabilities)):
        print(f"\n📝 Пример {i + 1}:")
        print(f"   Текст: {text}")
        print(f"   Предсказание: {pred}")
        print(f"   Уверенность: {conf:.3f}")

        # Детальные вероятности по классам
        print("   Вероятности по классам:")
        for label_idx, prob in enumerate(probs):
            label_name = label_map.get(label_idx, f"Класс {label_idx}")
            print(f"     {label_name}: {prob:.3f}")

        print("-" * 50)


# ==================== ТЕСТИРОВАНИЕ НА РЕАЛЬНЫХ ДАННЫХ ====================

def test_on_real_data(csv_path, num_samples=10):
    """Тестирование модели на реальных данных из CSV файла"""

    tokenizer, model = load_trained_model(config.MODEL_PATH)
    if model is None:
        return

    try:
        # Загрузка данных
        df = pd.read_csv(csv_path)

        # Берем случайные примеры
        samples = df.sample(min(num_samples, len(df)))

        print("\n" + "=" * 60)
        print(f"ТЕСТИРОВАНИЕ НА РЕАЛЬНЫХ ДАННЫХ ({len(samples)} примеров)")
        print("=" * 60)

        texts = samples['Review'].tolist()
        true_grades = samples['Grade'].tolist()

        # Преобразуем истинные оценки в тональность для сравнения
        def grade_to_sentiment(grade):
            grade = int(grade)
            if grade in [0, 1, 2]:
                return "Негативный"
            elif grade == 3:
                return "Нейтральный"
            else:
                return "Позитивный"

        true_sentiments = [grade_to_sentiment(grade) for grade in true_grades]

        # Предсказание
        predictions, confidences, probabilities, label_map = predict_sentiment(
            texts, model, tokenizer, device
        )

        # Сравнение предсказаний с истинными значениями
        correct = 0
        for i, (text, pred, true_sent, conf, grade) in enumerate(
                zip(texts, predictions, true_sentiments, confidences, true_grades)):
            is_correct = (pred == true_sent)
            if is_correct:
                correct += 1

            print(f"\n📊 Пример {i + 1} (Оценка: {grade}):")
            print(f"   Текст: {text[:100]}...")
            print(f"   Истинная тональность: {true_sent}")
            print(f"   Предсказание: {pred} {'✅' if is_correct else '❌'}")
            print(f"   Уверенность: {conf:.3f}")
            print("-" * 50)

        accuracy = correct / len(samples)
        print(f"\n🎯 ТОЧНОСТЬ НА ТЕСТОВЫХ ДАННЫХ: {accuracy:.1%} ({correct}/{len(samples)})")

    except Exception as e:
        print(f"❌ Ошибка при тестировании на реальных данных: {e}")


# ==================== ИНТЕРАКТИВНОЕ ТЕСТИРОВАНИЕ ====================

def interactive_test():
    """Интерактивное тестирование - ввод текста с клавиатуры"""

    tokenizer, model = load_trained_model(config.MODEL_PATH)
    if model is None:
        return

    print("\n" + "=" * 60)
    print("ИНТЕРАКТИВНОЕ ТЕСТИРОВАНИЕ")
    print("Вводите тексты для анализа тональности")
    print("Для выхода введите 'quit' или 'exit'")
    print("=" * 60)

    while True:
        user_input = input("\n🎯 Введите текст отзыва: ").strip()

        if user_input.lower() in ['quit', 'exit', 'выход']:
            break

        if not user_input:
            continue

        # Предсказание для одного текста
        predictions, confidences, probabilities, label_map = predict_sentiment(
            [user_input], model, tokenizer, device
        )

        print(f"\n🔍 Результат анализа:")
        print(f"   Тональность: {predictions[0]}")
        print(f"   Уверенность: {confidences[0]:.3f}")

        # Детальные вероятности
        print("   Детальные вероятности:")
        for label_idx, prob in enumerate(probabilities[0]):
            label_name = label_map.get(label_idx, f"Класс {label_idx}")
            print(f"     {label_name}: {prob:.3f}")


# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    print("🔧 ЗАГРУЗКА И ТЕСТИРОВАНИЕ ОБУЧЕННОЙ МОДЕЛИ")

    # Вариант 1: Тестирование на заранее подготовленных примерах
    test_model()

    # Вариант 2: Тестирование на реальных данных из вашего CSV (раскомментируйте если нужно)
    # test_on_real_data("result/filtered.csv", num_samples=10)

    # Вариант 3: Интерактивное тестирование (раскомментируйте если нужно)
    # interactive_test()