import pandas as pd
import numpy as np
import torch
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
import re
from tqdm.auto import tqdm
import warnings

warnings.filterwarnings('ignore')


# ==================== CONFIG ====================
class Config:
    MODEL_NAME = "cointegrated/rubert-tiny2"
    BATCH_SIZE = 16
    MAX_LENGTH = 256
    LEARNING_RATE = 2e-5
    EPOCHS = 3
    NUM_LABELS = 3

    # ОБНОВЛЕННЫЕ ПУТИ И НАЗВАНИЯ КОЛОНОК
    DATA_PATH = "result/good_filtered500.csv"  # ваш файл с новыми заголовками
    SAVE_PATH = "./bert_sentiment_model"
    SEED = 42


config = Config()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ==================== DATA PREPROCESSING ДЛЯ ВАШЕГО ФАЙЛА ====================

def load_and_preprocess_data(file_path):
    """Загрузка и предобработка данных ДЛЯ ВАШЕГО ФОРМАТА ФАЙЛА"""
    print("Загрузка данных...")

    # Чтение файла с вашими заголовками
    df = pd.read_csv(file_path)

    # ДИАГНОСТИКА: посмотрим на структуру данных
    print("Заголовки колонок в вашем файле:")
    print(df.columns.tolist())
    print(f"Всего строк: {len(df)}")

    # Фильтрация по статусу (если есть колонка Status)
    if 'Status' in df.columns:
        df = df[df['Status'] == "good"]
        print(f"После фильтрации Status=='good': {len(df)} строк")

    # Базовая очистка - используем вашу колонку Review
    df = df.dropna(subset=['Review'])
    df = df[df['Review'].str.len() > 10]

    # Проверяем наличие колонки Grade
    if 'Grade' not in df.columns:
        raise KeyError("Колонка 'Grade' не найдена в файле! Доступные колонки:", df.columns.tolist())

    # Создание меток тональности на основе Grade
    def create_sentiment_label(grade):
        """Преобразует оценку от 0 до 5 в метку тональности"""
        try:
            grade = int(grade)
            if grade in [0, 1, 2]:  # 0-2 → Негативный
                return 0
            elif grade == 3:  # 3 → Нейтральный
                return 1
            else:  # 4-5 → Позитивный
                return 2
        except (ValueError, TypeError):
            return 1  # По умолчанию нейтральный при ошибке

    df['label'] = df['Grade'].apply(create_sentiment_label)

    # Анализ распределения
    print("Распределение классов после создания меток:")
    label_counts = df['label'].value_counts()
    for label, count in label_counts.items():
        sentiment = ['Негативный', 'Нейтральный', 'Позитивный'][label]
        print(f"  {sentiment}: {count} отзывов ({count / len(df) * 100:.1f}%)")

    # Текстовая предобработка для колонки Review
    def clean_text(text):
        if isinstance(text, str):
            text = re.sub(r'http\S+', '', text)
            text = re.sub(r'\s+', ' ', text)
            text = text.strip().lower()
            return text
        return ""

    df['cleaned_review'] = df['Review'].apply(clean_text)

    # Удаляем строки, где текст стал слишком коротким после очистки
    df = df[df['cleaned_review'].str.len() > 5]

    print(f"Финальный размер датасета: {len(df)} отзывов")
    return df[['cleaned_review', 'label']]


# ==================== DATASET CLASS (БЕЗ ИЗМЕНЕНИЙ) ====================

class SentimentDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts.iloc[idx])
        label = self.labels.iloc[idx]

        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


# ==================== ОСНОВНОЙ КОД С АДАПТАЦИЕЙ ====================

def main():
    try:
        # 1. Загрузка данных ИМЕННО ИЗ ВАШЕГО ФАЙЛА
        print("=== ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ ===")
        data = load_and_preprocess_data(config.DATA_PATH)

        # 2. Разделение на train/validation - ТЕПЕРЬ РАБОТАЕТ С ВАШИМИ ДАННЫМИ
        train_texts, val_texts, train_labels, val_labels = train_test_split(
            data['cleaned_review'],
            data['label'],
            test_size=0.2,
            random_state=config.SEED,
            stratify=data['label']
        )

        print(f"Размер тренировочной выборки: {len(train_texts)}")
        print(f"Размер валидационной выборки: {len(val_texts)}")

        # 3. Загрузка токенизатора и модели
        print("\n=== ЗАГРУЗКА МОДЕЛИ И ТОКЕНИЗАТОРА ===")
        tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)

        model = AutoModelForSequenceClassification.from_pretrained(
            config.MODEL_NAME,
            num_labels=config.NUM_LABELS
        )
        model = model.to(device)

        # 4. Создание DataLoader
        train_dataset = SentimentDataset(train_texts, train_labels, tokenizer, config.MAX_LENGTH)
        val_dataset = SentimentDataset(val_texts, val_labels, tokenizer, config.MAX_LENGTH)

        train_loader = DataLoader(train_dataset, batch_size=config.BATCH_SIZE, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=config.BATCH_SIZE, shuffle=False)

        # 5. Настройка оптимизатора
        optimizer = AdamW(model.parameters(), lr=config.LEARNING_RATE)
        total_steps = len(train_loader) * config.EPOCHS
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=0,
            num_training_steps=total_steps
        )

        # 6. Обучение
        print("\n=== НАЧАЛО ОБУЧЕНИЯ ===")
        best_accuracy = 0

        for epoch in range(config.EPOCHS):
            print(f"\n--- Эпоха {epoch + 1}/{config.EPOCHS} ---")

            # Обучение
            train_loss, train_acc = train_epoch(model, train_loader, optimizer, scheduler, device)

            # Валидация
            val_loss, val_acc, val_f1, val_preds, val_true = eval_model(model, val_loader, device)

            print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
            print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}, Val F1: {val_f1:.4f}")

            # Сохранение лучшей модели
            if val_acc > best_accuracy:
                best_accuracy = val_acc
                model.save_pretrained(config.SAVE_PATH)
                tokenizer.save_pretrained(config.SAVE_PATH)
                print(f"✅ Модель сохранена! Точность: {val_acc:.4f}")

        # 7. Финальная оценка
        print("\n=== ФИНАЛЬНАЯ ОЦЕНКА ===")
        model = AutoModelForSequenceClassification.from_pretrained(config.SAVE_PATH)
        model = model.to(device)

        _, final_acc, final_f1, final_preds, final_true = eval_model(model, val_loader, device)

        print(f"Финальная точность: {final_acc:.4f}")
        print(f"Финальный F1-score: {final_f1:.4f}")

        print("\nОтчет по классификации:")
        print(classification_report(
            final_true,
            final_preds,
            target_names=['Негативный', 'Нейтральный', 'Позитивный']
        ))

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("Проверьте:")
        print("1. Правильность пути к файлу")
        print("2. Наличие колонок 'Review' и 'Grade' в файле")
        print("3. Корректность данных в этих колонках")


# ==================== ФУНКЦИИ ОБУЧЕНИЯ И ОЦЕНКИ ====================

def train_epoch(model, data_loader, optimizer, scheduler, device):
    """Одна эпоха обучения"""
    model.train()
    losses = []
    correct_predictions = 0

    progress_bar = tqdm(data_loader, desc="Training")

    for batch in progress_bar:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['labels'].to(device)

        optimizer.zero_grad()

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )

        loss = outputs.loss
        logits = outputs.logits

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

        losses.append(loss.item())
        preds = torch.argmax(logits, dim=1)
        correct_predictions += torch.sum(preds == labels)

        progress_bar.set_postfix({
            'loss': np.mean(losses[-10:]),
            'acc': correct_predictions.double().item() / (len(progress_bar) * config.BATCH_SIZE)
        })

    return np.mean(losses), correct_predictions.double() / len(data_loader.dataset)


def eval_model(model, data_loader, device):
    """Валидация модели"""
    model.eval()
    losses = []
    correct_predictions = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in tqdm(data_loader, desc="Validation"):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )

            loss = outputs.loss
            logits = outputs.logits

            losses.append(loss.item())
            preds = torch.argmax(logits, dim=1)
            correct_predictions += torch.sum(preds == labels)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    accuracy = correct_predictions.double() / len(data_loader.dataset)
    f1 = f1_score(all_labels, all_preds, average='weighted')

    return np.mean(losses), accuracy, f1, all_preds, all_labels


# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    main()