import datetime
import time
import json
import threading
from dataclasses import dataclass, asdict
from typing import Optional
import csv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)



@dataclass
class Result:
    url: str
    grade: int
    grade_accepted: bool
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
    date: str


class Parser:
    """
    Синхронная версия Parser'а без прокси.
    Сохраняет поведение оригинального асинхронного варианта:
    - одношаговый shared driver
    - пересоздание драйвера при WebDriverException / OSError (максимум max_retries_on_session)
    - сохранение результатов с защитой lock
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: list[Result] = []
        self.lock = threading.Lock()   # защита при добавлении в results
        self.counter = 1
        self.driver: Optional[webdriver.Chrome] = None
        self.max_retries_on_session = 1  # при падении сессии пересоздаём драйвер и повторяем

    def _create_driver(self) -> webdriver.Chrome:
        """Создаёт и возвращает новый Chrome WebDriver с оптимизациями для скорости."""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # Небольшой implicit wait только как запас; используем explicit waits
        driver.implicitly_wait(0.5)
        return driver

    def _close_driver_sync(self):
        """Синхронное закрытие драйвера (без ошибок)."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None

    def _ensure_driver_sync(self):
        """Гарантирует наличие инициализированного драйвера (синхронно)."""
        if self.driver is None:
            self.driver = self._create_driver()

    def _parse_page_content_sync(self, driver: webdriver.Chrome, url: str, page_num: int, proxy_used: bool) -> Result:
        """Синхронный парсер содержимого страницы (как в вашем оригинале)."""
        try:
            html = driver.page_source
            if not html:
                return Result(url=url, grade=0, product="", review="", bank="", status="Error: No content",
                              proxy_used=proxy_used, clear_conditions=0, polite_employee=0, availability=0,
                              convenience=0, city="")

            # title
            try:
                title_el = driver.find_element(By.TAG_NAME, "title")
                title_text = title_el.get_attribute("textContent").strip()
            except NoSuchElementException:
                title_text = "No title"

            # review
            review = "Review element not found"
            try:
                review_div = WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        "div.MarkdownInsidestyled__MarkdownInsideStyled-sc-1frtivc-0.bKVLHc"))
                )
                try:
                    review_p = review_div.find_elements(By.TAG_NAME, "p")
                    review = ""
                    for p in review_p:
                        review += p.text + " "
                except NoSuchElementException:
                    review = review_div.text
            except TimeoutException:
                review = "Review element not found"

            parent_grade_div = driver.find_element(By.CSS_SELECTOR, "div.lbb810226")

            # grade
            grade_accepted = False
            grade = 0
            for i in range(5):
                try:
                    grade_div = parent_grade_div.find_element(
                        By.CSS_SELECTOR,
                         f"div[class^='rating-grade rating-grade--color-{i}']"
                    )
                    text = grade_div.text.strip()
                    if text.isdigit():
                        grade = int(text)
                        if i == 0:
                            grade_accepted = False
                        else:
                            grade_accepted = True
                        break
                except NoSuchElementException:
                    continue

            #datetime
            date_time = "0"
            try:
                date_element = driver.find_element(By.CSS_SELECTOR, "span.l10fac986")
                date_time = date_element.text.strip()




            except NoSuchElementException:
                pass



            # product / bank
            product = "Unknown"
            bank = "Unknown"
            try:
                title_text = driver.title

                # Ищем позиции
                start_pos = title_text.find('–') + 1  # +1 чтобы исключить сам символ -
                end_pos = title_text.find('от')

                if start_pos != -1 and end_pos != -1 and end_pos > start_pos:
                    bank = title_text[start_pos:end_pos].strip()
                    bank = title_text
                else:
                    bank = "Unknown"  # или какое-то значение по умолчанию
            except Exception:
                pass
            try:
                product_element = driver.find_element(By.CSS_SELECTOR,
                                                      "h2.page-section__header.page-section__header-bottom-indent")
                if product_element:
                    product_text = product_element.text.strip()
                    parts = product_text.split()
                    product = product_text
            except NoSuchElementException:
                pass

            # extended grades
            clear_conditions = polite_employee = availability = convenience = 0
            try:
                extended_grade = driver.find_elements(By.CSS_SELECTOR, "div.ld017b199")
                if len(extended_grade) >= 1:
                    clear_conditions = len(extended_grade[0].find_elements(By.CSS_SELECTOR, "div.l61f54b7b"))
                if len(extended_grade) >= 2:
                    polite_employee = len(extended_grade[1].find_elements(By.CSS_SELECTOR, "div.l61f54b7b"))
                if len(extended_grade) >= 3:
                    availability = len(extended_grade[2].find_elements(By.CSS_SELECTOR, "div.l61f54b7b"))
                if len(extended_grade) >= 4:
                    convenience = len(extended_grade[3].find_elements(By.CSS_SELECTOR, "div.l61f54b7b"))
            except Exception:
                pass

            city = "Unknown"
            try:
                city_element = driver.find_element(By.CSS_SELECTOR, "span.l3a372298")
                city = city_element.text if city_element else "Unknown"
            except NoSuchElementException:
                pass

            return Result(
                url=url,
                grade=grade,
                product=product,
                review=review,
                bank=bank,
                status="good",
                proxy_used=proxy_used,
                clear_conditions=clear_conditions,
                polite_employee=polite_employee,
                availability=availability,
                date = date_time,
                grade_accepted=grade_accepted,
                convenience=convenience,
                city=city,
            )

        except Exception as e:
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
                date=None,
                grade_accepted=False,
                availability=0,
                convenience=0,
                city="",
            )

    def process_single_page(self, page_num: int, use_proxy: bool = False) -> Result:
        """
        Синхронная обработка одной страницы: driver.get + парсинг.
        При падении сессии пересоздаём драйвер и повторяем (max_retries_on_session).
        """
        url = f"{self.base_url}{page_num}"
        attempts = 0
        last_exc = None

        while attempts <= self.max_retries_on_session:
            attempts += 1
            # Убедимся, что драйвер есть
            try:
                self._ensure_driver_sync()
            except Exception as e:
                last_exc = e
                print(f"Failed to create driver (attempt {attempts}): {e!r}")
                time.sleep(1)
                continue

            try:
                # driver.get и ожидание readyState
                self.driver.get(url)
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except Exception:
                    # если не успело — идём дальше; explicit waits ниже поймают нужные элементы
                    pass

                # парсим синхронно
                result = self._parse_page_content_sync(self.driver, url, page_num, use_proxy)

                # сохраняем результат
                with self.lock:
                    self.results.append(result)
                    self.counter += 1

                print(f"[{'PROXY' if use_proxy else 'DIRECT'}] Page {page_num}: {result.status}")
                return result

            except (WebDriverException, OSError) as e:
                # Сессия упала — закроем и пересоздадим драйвер, затем повторим
                last_exc = e
                print(f"WebDriverException on page {page_num}: {e!r}. Recreating driver (attempt {attempts})...")
                try:
                    self._close_driver_sync()
                except Exception:
                    pass
                time.sleep(1)
                # следующая итерация создаст драйвер вновь
                continue

            except Exception as e:
                # Неожиданная ошибка — завершаем и возвращаем Result с ошибкой
                print(f"Unhandled error for page {page_num}: {e!r}")
                res = Result(
                    url=url, grade=0, product="", review="", bank="", status=f"Error:{e}", proxy_used=use_proxy,
                    clear_conditions=0, polite_employee=0, availability=0, convenience=0, city=""
                )
                with self.lock:
                    self.results.append(res)
                    self.counter += 1
                return res

        # Если попытки исчерпаны
        print(f"Failed to process page {page_num} after retries. Last exception: {last_exc!r}")
        res = Result(
            url=url, grade=0, product="", review="", bank="", status=f"Error: failed after retries {last_exc}",
            proxy_used=use_proxy, clear_conditions=0, polite_employee=0, availability=0, convenience=0, city=""
        )
        with self.lock:
            self.results.append(res)
            self.counter += 1
        return res

    def run_direct_connection(self, start_page: int, end_page: int):
        """Запуск парсинга: создаём драйвер один раз и обрабатываем страницы последовательно."""
        print("Starting direct connection parsing with single shared driver...")
        # создаём драйвер заранее
        self._ensure_driver_sync()

        try:
            for page_num in range(start_page, end_page + 1):
                try:
                    self.process_single_page(page_num, use_proxy=False)
                except Exception as e:
                    print(f"Error processing page {page_num}: {e!r}")
                # короткая пауза чтобы не бить сервер и дать CPU отработать
                time.sleep(0.1)
        finally:
            # закрываем драйвер в любом случае
            self._close_driver_sync()

    def save_results(self, filename: str = "parsed_results.json"):
        results_dict = []
        for result in self.results:
            d = asdict(result)
            d["timestamp"] = time.time()
            results_dict.append(d)
        with open(filename, "a", encoding="utf-8") as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {filename}")

    def save_results_csv(self, filename: str = "parsed_results.csv", firststart: bool = False):


        with open(filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if firststart:
                writer.writerow([
                    'URL', 'Grade', 'Grade Accepted', 'Bank', 'Review', 'Product',
                    'Proxy Used', 'Status', 'Clear Conditions', 'Polite Employee',
                    'Availability', 'Convenience', 'City', 'Date'
                ])
            for result in self.results:
                writer.writerow([
                    result.url,
                    result.grade,
                    result.grade_accepted,
                    result.bank,
                    (result.review[:100] + "...") if len(result.review) > 100 else result.review,
                    result.product,
                    result.proxy_used,
                    result.status,
                    result.clear_conditions,
                    result.polite_employee,
                    result.availability,
                    result.convenience,
                    result.city,
                    result.date
                ])
        print(f"Results saved to {filename}")


# Пример синхронного main'а для запуска (alpha-версия, похожая на ваш оригинал)
def main_sync(startpage, endpage, firststart = False):
    BASE_URL = "https://www.banki.ru/services/responses/bank/response/"

    parser = Parser(base_url=BASE_URL)

    start_time = time.time()
    try:
        # уменьшённый диапазон для теста; замените на нужный вам
        parser.run_direct_connection(startpage, endpage)
    except Exception as e:
        print(f"Error during parsing: {e!r}")
    finally:
        # на всякий случай
        parser._close_driver_sync()

    end_time = time.time()
    print(f"\nParsing completed in {end_time - start_time:.2f} seconds")
    print(f"Total pages processed: {len(parser.results)}")
    unique_urls = set(r.url for r in parser.results)
    print(f"Unique URLs: {len(unique_urls)}")
    for u in unique_urls:
        print(f"  - {u}")

    parser.save_results_csv("result/parsing_results31_10.csv", firststart=firststart)


if __name__ == "__main__":
    start = 12622410
    end = 12650570

    for i in range(start, end, 10):
       if i == start:
            main_sync(i, i + 9, firststart=True)
       else:
           main_sync(i, i+9, firststart=False)