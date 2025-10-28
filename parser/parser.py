import aiohttp
import asyncio
import json
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass, asdict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from typing import List, Optional
import random
from dotenv import find_dotenv, load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class Result:
    url: str
    grade: int
    bank: str
    review: str
    product: str
    proxy_used: bool
    status: str
    clear_conditions: int
    polite_employee: int
    availability: int
    convenience: int
    city: str


class Parser:
    def __init__(self, base_url, proxy=False, proxy_url=None):
        self.base_url = base_url
        self.proxy_url = proxy_url
        self.results = []
        self.lock = threading.Lock()
        self.counter = 1
        self.driver = None

    def setup_driver(self):
        """Настройка и инициализация WebDriver"""
        chrome_options = Options()
        # Убираем headless для отладки
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        if self.proxy_url:
            chrome_options.add_argument(f'--proxy-server={self.proxy_url}')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        # Устанавливаем неявное ожидание
        self.driver.implicitly_wait(3)
        return self.driver

    def close_driver(self):
        """Закрытие WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    async def fetch_with_selenium(self, page_num, use_proxy=False):
        """Загрузка страницы с использованием Selenium"""
        url = f"{self.base_url}{page_num}"
        print(f"Loading URL: {url}")

        try:
            if not self.driver:
                self.setup_driver()

            self.driver.get(url)
            # Ждем загрузки страницы
            await asyncio.sleep(5)

            return self.driver, True

        except Exception as e:
            return None, f"Selenium error: {str(e)}"

    def wait_for_element(self, by, selector, timeout=10):
        """Ожидание появления элемента"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            return None

    def find_element_safe(self, by, selector, default=None):
        """Безопасный поиск элемента с обработкой исключений"""
        try:
            return self.driver.find_element(by, selector)
        except NoSuchElementException:
            return default

    def find_elements_safe(self, by, selector):
        """Безопасный поиск элементов с обработкой исключений"""
        try:
            return self.driver.find_elements(by, selector)
        except NoSuchElementException:
            return []

    async def parse_page_content(self, url, driver, page_num, proxy_used):
        """Парсинг содержимого страницы с использованием Selenium"""

        try:
            # Получаем HTML страницы для проверки контента
            html = driver.page_source
            if not html:
                return Result(
                    url=url,
                    grade=0,
                    product="",
                    review="",
                    bank="",
                    status="Error: No content",
                    proxy_used=proxy_used,
                    clear_conditions=0,
                    polite_employee=0,
                    availability=0,
                    convenience=0,
                    city=""
                )

            # Ожидаем загрузки ключевых элементов
            print("Waiting for page elements to load...")

            # Ждем заголовок
            title = self.find_element_safe(By.TAG_NAME, 'title')
            title_text = title.get_attribute('textContent').strip() if title else "No title"

            # Ждем и получаем отзыв
            review_div = self.wait_for_element(
                By.CSS_SELECTOR,
                'div.MarkdownInsidestyled__MarkdownInsideStyled-sc-1frtivc-0.bKVLHc',
                timeout=15
            )

            if not review_div:
                # Пробуем альтернативные селекторы
                review_div = self.wait_for_element(
                    By.CSS_SELECTOR,
                    'div[class*="MarkdownInsideStyled"]',
                    timeout=10
                )

            if review_div:
                try:
                    review_p = review_div.find_element(By.TAG_NAME, 'p')
                    review = review_p.text
                except NoSuchElementException:
                    review = review_div.text
            else:
                review = "Review element not found"

            # Получаем оценку
            grade_div = None
            for i in range(1, 6):
                grade_div = self.find_element_safe(
                    By.CSS_SELECTOR,
                    f'div.rating-grade.rating-grade--color-{i}.rating-grade--filled'
                )
                if grade_div:
                    break

            if not grade_div:
                # Если не нашли по конкретному цвету, ищем любой заполненный
                grade_div = self.find_element_safe(
                    By.CSS_SELECTOR,
                    'div.rating-grade.rating-grade--filled'
                )

            grade = grade_div.text if grade_div else "0"

            # Извлекаем продукт и банк
            product_element = self.wait_for_element(
                By.CSS_SELECTOR,
                'h2.page-section__header.page-section__header-bottom-indent',
                timeout=10
            )

            if product_element:
                product_text = product_element.text
                product_parts = product_text.split()
                product = product_parts[2] if len(product_parts) > 2 else "Unknown"
                bank = ' '.join(product_parts[-2:]) if len(product_parts) >= 2 else "Unknown"
            else:
                product = "Unknown"
                bank = "Unknown"

            # Извлекаем расширенные оценки
            extended_grade = self.find_elements_safe(By.CSS_SELECTOR, 'div.ld017b199')

            clear_conditions = 0
            polite_employee = 0
            availability = 0
            convenience = 0

            if len(extended_grade) >= 1:
                clear_conditions = len(extended_grade[0].find_elements(By.CSS_SELECTOR, 'div.l61f54b7b'))
            if len(extended_grade) >= 2:
                polite_employee = len(extended_grade[1].find_elements(By.CSS_SELECTOR, 'div.l61f54b7b'))
            if len(extended_grade) >= 3:
                availability = len(extended_grade[2].find_elements(By.CSS_SELECTOR, 'div.l61f54b7b'))
            if len(extended_grade) >= 4:
                convenience = len(extended_grade[3].find_elements(By.CSS_SELECTOR, 'div.l61f54b7b'))

            # Извлекаем город
            city_element = self.find_element_safe(By.CSS_SELECTOR, 'span.l3a372298')
            city = city_element.text if city_element else "Unknown"

            print(f"Successfully parsed page {page_num}")

            return Result(
                url=url,
                grade=int(grade) if grade.isdigit() else 0,
                product=product,
                review=review,
                bank=bank,
                status="good",
                proxy_used=proxy_used,
                clear_conditions=clear_conditions,
                polite_employee=polite_employee,
                availability=availability,
                convenience=convenience,
                city=city
            )

        except Exception as e:
            print(f"Error parsing page {page_num}: {str(e)}")
            return Result(
                url=url,
                grade=0,
                product="",
                review="",
                bank="",
                status=f"Error:{e}",
                proxy_used=proxy_used,
                clear_conditions=0,
                polite_employee=0,
                availability=0,
                convenience=0,
                city=""
            )

    async def process_single_page(self, url, page_num, use_proxy=False):
        """Обработка одной страницы с использованием Selenium"""
        driver, proxy_used = await self.fetch_with_selenium(page_num, use_proxy)

        if driver is None:
            result = Result(
                url=url,
                grade=0,
                product="",
                review="",
                bank="",
                status=f"Error: Failed to load page - {proxy_used}",
                proxy_used=use_proxy,
                clear_conditions=0,
                polite_employee=0,
                availability=0,
                convenience=0,
                city=""
            )
        else:
            result = await self.parse_page_content(driver, page_num, proxy_used)

        # Добавляем сквозную нумерацию
        with self.lock:
            self.results.append(result)
            self.counter += 1

        print(f"[{'PROXY' if proxy_used else 'DIRECT'}] Page {page_num}: {result.status}")
        return result

    async def run_direct_connection(self, start_page, end_page):
        """Запуск парсинга через прямое соединение с Selenium"""
        print("Starting direct connection parsing with Selenium...")

        tasks = []
        for page_num in range(start_page, end_page + 1):
            task = self.process_single_page(page_num, use_proxy=False)
            tasks.append(task)
            # Задержка чтобы не перегружать сервер
            await asyncio.sleep(3)

        await asyncio.gather(*tasks, return_exceptions=True)

        # Закрываем драйвер после завершения
        self.close_driver()

    async def run_proxy_connection(self, start_page, end_page):
        """Запуск парсинга через прокси с Selenium"""
        if not self.proxy_url:
            print("No proxy URL provided, skipping proxy parsing")
            return

        print("Starting proxy connection parsing with Selenium...")

        tasks = []
        for page_num in range(start_page, end_page + 1):
            task = self.process_single_page(page_num, use_proxy=True)
            tasks.append(task)
            # Задержка для прокси
            await asyncio.sleep(4)

        await asyncio.gather(*tasks, return_exceptions=True)

        # Закрываем драйвер после завершения
        self.close_driver()

    def save_results(self, filename="parsed_results.json"):
        """Сохранение результатов в JSON файл"""
        results_dict = []
        for result in self.results:
            result_dict = asdict(result)
            result_dict["timestamp"] = time.time()
            results_dict.append(result_dict)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {filename}")

    def save_results_csv(self, filename="parsed_results.csv"):
        """Сохранение результатов в CSV файл"""
        import csv

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Grade', 'Product', 'Review', 'Bank', 'Status', 'Proxy Used',
                             'Clear Conditions', 'Polite Employee', 'Availability', 'Convenience', 'City'])

            for result in self.results:
                writer.writerow([
                    result.url,
                    result.grade,
                    result.product,
                    result.review[:100] + "..." if len(result.review) > 100 else result.review,
                    # Обрезаем длинные отзывы
                    result.bank,
                    result.status,
                    result.proxy_used,
                    result.clear_conditions,
                    result.polite_employee,
                    result.availability,
                    result.convenience,
                    result.city
                ])

        print(f"Results saved to {filename}")


async def main():
    # Настройки парсера
    BASE_URL = "https://www.banki.ru/services/responses/bank/response/"
    PROXY_URL = None  # Установите ваш прокси если нужно

    # Создаем парсер
    parser = Parser(
        base_url=BASE_URL,
        proxy=False,
        proxy_url=PROXY_URL
    )

    # Запускаем парсинг
    start_time = time.time()

    try:
        # Парсим одну страницу через прямое соединение
        await parser.run_direct_connection(12650560, 12650570)

    except Exception as e:
        print(f"Error during parsing: {e}")
    finally:
        # Гарантируем закрытие драйвера
        parser.close_driver()

    end_time = time.time()

    print(f"\nParsing completed in {end_time - start_time:.2f} seconds")
    print(f"Total pages processed: {len(parser.results)}")

    # Сохраняем результаты
    parser.save_results("parsing_results.json")
    #parser.save_results_csv("parsing_results.csv")


if __name__ == "__main__":
    asyncio.run(main())