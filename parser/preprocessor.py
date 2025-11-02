
import os
import re
import pandas as pd


pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)



def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def process_bank_column(df):

    def extract_bank_name(row):
        bank_text = row['Bank']
        product_text = row['Product']

        # Обработка случая Unknown
        if bank_text == 'Unknown' and pd.notna(product_text) and isinstance(product_text, str):
            # Берем 2 последних слова из Product
            words = product_text.strip().split()
            if len(words) >= 2:
                result = ' '.join(words[-2:])
            elif len(words) == 1:
                result = words[0]
            else:
                result = bank_text

            if result.endswith('а'):
                result = result[:-1]
            if 'банка' in result.lower():
                result = re.sub(r'Банка', 'Банк', result, flags=re.IGNORECASE)

            stop_words = ["продуктах", "картах", "ипотеке", "вкладах", "кредитах"]
            for word in stop_words:
                result = re.sub(r'\b' + word + r'\b', '', result, flags=re.IGNORECASE)

            # Убираем лишние пробелы
            result = re.sub(r'\s+', ' ', result).strip()


            return result

        if pd.isna(bank_text) or not isinstance(bank_text, str) or bank_text == 'Unknown':
            return bank_text



        # Ищем паттерн: " – отзыв о " + 2 слова
        pattern = r' – отзыв о\s+(\S+\s+\S+)'
        match = re.search(pattern, bank_text)

        if match:
            # Извлекаем 2 слова после " – отзыв о "
            result = match.group(1)
            # Удаляем символы "от" из полученной строки
            result = result.replace('от', '')
            # Убираем лишние пробелы
            result = re.sub(r'\s+', ' ', result).strip()

            # Удаляем последнюю букву "е" если она есть
            if result.endswith('е'):
                result = result[:-1]
            # Или ищем "банке" в любом регистре и удаляем "е"
            elif re.search(r'банке', result, re.IGNORECASE):
                result = re.sub(r'банке', 'Банк', result, flags=re.IGNORECASE)

            return result
        else:
            # Если паттерн не найден, возвращаем исходный текст
            return bank_text

    def process_Product(row):
        product_text = row['Product']
        stop_words = {"продуктах":"все продукты", "дебетовых картах": "дебетовая карта", "ипотеке": "ипотека", "вкладах":"вклады", "кредитах":"кредиты", "кредитных":"кредитная карта","РКО":"РКО","Unknown":"все продукты"}
        for i in stop_words.keys():
            if i in product_text:
                product_text =  stop_words.get(i)
        return product_text
    # Применяем функцию к каждой строке DataFrame
    df['Bank'] = df.apply(extract_bank_name, axis=1)
    df['Product'] = df.apply(process_Product, axis=1)
    mask = (df['Bank'] == 'Unknown')
    df = df.drop(df[mask].index)


    return df

def preprocess_csv(in_path: str, out_path: str):

    df = pd.read_csv(in_path)
    df_filt = df[df['Status'] == "good"]
    df_filt = df_filt.dropna(subset=['Review'])

    df_filt = df_filt.drop_duplicates(subset=['Review'])
    df_filt.to_csv(out_path)

if __name__ == "__main__":
    df = pd.read_csv("result/another_parsing_results_02_11.csv")
    df = df.dropna(subset=['Review']).drop_duplicates(subset=['Review'])

    df = process_bank_column(df)
    try:
        df = df.drop(columns=['Unnamed: 0'])
    except KeyError as e:
        print(e)
    df = df.drop(4290)
    df.to_csv("result/filtered.csv")