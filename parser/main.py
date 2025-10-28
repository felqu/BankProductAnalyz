import asyncio
import json
import time
import threading
from dataclasses import dataclass, asdict
from typing import Optional

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
# остальное оставлено из вашего оригинала (BeautifulSoup и т.д.) при необходимости можно вернуть


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
    def __init__(self, base_url: str, proxy_url: Optional[str] = None):
        self.base_url = base_url
        self.proxy_url = proxy_url
        self.results: list[Result] = []
        self.lock = threading.Lock()   # защита при добавлении в results
        self.counter = 1
        self.driver: Optional[webdriver.Chrome] = None
        self.selenium_lock = asyncio.Lock()  # сериализация доступа к driver
        self.max_retries_on_session = 1  # при падении сессии пересоздаём драйвер и повторяем

    def _create_driver(self) -> webdriver.Chrome:
        """Создаёт и возвращает новый Chrome WebDriver с оптимизациями для скорости."""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Отключаем загрузку тяжёлых ресурсов (экономит время)
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        if self.proxy_url:
            chrome_options.add_argument(f"--proxy-server={self.proxy_url}")

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

    async def _ensure_driver(self):
        """Асинхронно гарантирует наличие инициализированного драйвера (создание в потоке)."""
        if self.driver is None:
            self.driver = await asyncio.to_thread(self._create_driver)

    def _parse_page_content_sync(self, driver: webdriver.Chrome, url: str, page_num: int, proxy_used: bool) -> Result:
        """Синхронный парсер, который должен выполняться в потоке (в том же потоке, где выполнен driver.get)."""
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
                    review_p = review_div.find_element(By.TAG_NAME, "p")
                    review = review_p.text
                except NoSuchElementException:
                    review = review_div.text
            except TimeoutException:
                review = "Review element not found"

            # grade
            grade = 0
            for i in range(1, 6):
                try:
                    grade_div = driver.find_element(
                        By.CSS_SELECTOR,
                        f"div.rating-grade.rating-grade--color-{i}.rating-grade--filled"
                    )
                    text = grade_div.text.strip()
                    if text.isdigit():
                        grade = int(text)
                        break
                except NoSuchElementException:
                    continue

            # product / bank
            product = "Unknown"
            bank = "Unknown"
            try:
                product_element = driver.find_element(By.CSS_SELECTOR,
                                                      "h2.page-section__header.page-section__header-bottom-indent")
                if product_element:
                    product_text = product_element.text.strip()
                    parts = product_text.split()
                    product = parts[2] if len(parts) > 2 else "Unknown"
                    bank = " ".join(parts[-2:]) if len(parts) >= 2 else "Unknown"
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
                availability=0,
                convenience=0,
                city="",
            )

    async def process_single_page(self, page_num: int, use_proxy: bool = False) -> Result:
        """Асинхронно обрабатывает одну страницу: делает driver.get + парсинг в потоке с защитой."""
        url = f"{self.base_url}{page_num}"
        attempts = 0
        last_exc = None

        while attempts <= self.max_retries_on_session:
            attempts += 1
            # Сериализуем доступ к driver
            async with self.selenium_lock:
                # Убедимся, что драйвер есть
                try:
                    await self._ensure_driver()
                except Exception as e:
                    last_exc = e
                    print(f"Failed to create driver (attempt {attempts}): {e!r}")
                    await asyncio.sleep(1)
                    continue

                # Выполняем blocking операции в потоке
                try:
                    def sync_flow():
                        # driver.get и ожидание readyState
                        self.driver.get(url)
                        try:
                            WebDriverWait(self.driver, 10).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                        except Exception:
                            # если не успело — идём дальше; explicit waits ниже поймают нужные элементы
                            pass
                        # сразу парсим синхронно
                        return self._parse_page_content_sync(self.driver, url, page_num, use_proxy)

                    result = await asyncio.to_thread(sync_flow)

                    # Сохраняем результат
                    with self.lock:
                        self.results.append(result)
                        self.counter += 1

                    print(f"[{'PROXY' if use_proxy else 'DIRECT'}] Page {page_num}: {result.status}")
                    return result

                except (WebDriverException, OSError) as e:
                    # Сессия упала — закроем и пересоздадим драйвер, затем повторим (limit = max_retries_on_session)
                    last_exc = e
                    print(f"WebDriverException on page {page_num}: {e!r}. Recreating driver (attempt {attempts})...")
                    try:
                        await asyncio.to_thread(self._close_driver_sync)
                    except Exception:
                        pass
                    # небольшая пауза перед пересозданием
                    await asyncio.sleep(1)
                    try:
                        # пересоздание в следующей итерации _ensure_driver() вызовется снова
                        continue
                    except Exception as e2:
                        last_exc = e2
                        print(f"Failed to recreate driver: {e2!r}")
                        await asyncio.sleep(1)
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

    async def run_direct_connection(self, start_page: int, end_page: int):
        """Запуск парсинга: создаём драйвер один раз и обрабатываем страницы последовательно."""
        print("Starting direct connection parsing with single shared driver...")
        # создаём драйвер заранее
        await self._ensure_driver()

        try:
            for page_num in range(start_page, end_page + 1):
                try:
                    await self.process_single_page(page_num, use_proxy=False)
                except Exception as e:
                    print(f"Error processing page {page_num}: {e!r}")
                # короткая пауза чтобы не бить сервер и дать CPU отработать
                await asyncio.sleep(0.1)
        finally:
            # закрываем драйвер в любом случае
            await asyncio.to_thread(self._close_driver_sync)

    def save_results(self, filename: str = "parsed_results.json"):
        results_dict = []
        for result in self.results:
            d = asdict(result)
            d["timestamp"] = time.time()
            results_dict.append(d)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {filename}")

    def save_results_csv(self, filename: str = "parsed_results.csv"):
        import csv
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Grade', 'Product', 'Review', 'Bank', 'Status', 'Proxy Used',
                             'Clear Conditions', 'Polite Employee', 'Availability', 'Convenience', 'City'])
            for result in self.results:
                writer.writerow([
                    result.url,
                    result.grade,
                    result.product,
                    (result.review[:100] + "...") if len(result.review) > 100 else result.review,
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
    BASE_URL = "https://www.banki.ru/services/responses/bank/response/"
    PROXY_URL = None

    parser = Parser(base_url=BASE_URL, proxy_url=PROXY_URL)

    start_time = time.time()
    try:
        # уменьшённый диапазон для теста; замените на нужный вам
        await parser.run_direct_connection(12650560, 12650570)
    except Exception as e:
        print(f"Error during parsing: {e!r}")
    finally:
        # на всякий случай
        await asyncio.to_thread(parser._close_driver_sync)

    end_time = time.time()
    print(f"\nParsing completed in {end_time - start_time:.2f} seconds")
    print(f"Total pages processed: {len(parser.results)}")
    unique_urls = set(r.url for r in parser.results)
    print(f"Unique URLs: {len(unique_urls)}")
    for u in unique_urls:
        print(f"  - {u}")

    parser.save_results("parsing_results1.json")


if __name__ == "__main__":
    asyncio.run(main())
