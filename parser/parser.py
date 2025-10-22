import aiohttp
import asyncio
import json
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
from typing import List, Optional
import random
from dotenv import find_dotenv, load_dotenv


@dataclass
class Result:
    url: str
    grade: int
    title: str
    review: str
    product: str
    proxy_used: bool
    status: str

class Parser:
    def __init__(self, base_url, max_pages, proxy=False, proxy_url=None):
        self.base_url = base_url
        self.max_pages = max_pages
        self.proxy_url = proxy_url
        self.results = []
        self.lock = threading.Lock()
        self.counter = 1

    async def fetch_page(self, session, page_num, use_proxy=False):
        """Загрузка страницы с использованием прокси или прямого соединения"""
        url = f"{self.base_url}/{page_num}"

        connector = None
        if use_proxy and self.proxy_url:
            connector = aiohttp.TCPConnector()

        try:
            if use_proxy and self.proxy_url:
                async with session.get(url, proxy=self.proxy_url, timeout=30) as response:
                    return await response.text(), response.status, True
            else:
                async with session.get(url, timeout=30) as response:
                    return await response.text(), response.status, False

        except Exception as e:
            return None, str(e), use_proxy

    async def parse_page_content(self, html, page_num, proxy_used):
        """Парсинг содержимого страницы"""
        if not html:
            return Result(
                url=page_num,
                grade=0,
                product="",
                review="",
                title="",
                status="Error: No content",
                proxy_used=proxy_used
            )

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Извлекаем заголовок
            title = soup.find('title')
            title_text = title.text.strip() if title else "No title"
            #получаем сам отзыв
            div_element = soup.find('div', class_='MarkdownInsidestyled__MarkdownInsideStyled-sc-1frtivc-0 bKVLHc')
            review = div_element.find('p').get_text()

            # Извлекаем основной контент (пример)
            content_elements = soup.find_all(['p', 'div.content', 'article'])
            content_preview = ' '.join([elem.get_text(strip=True) for elem in content_elements[:3]])[:200] + "..."

            return Result(
                url=page_num,
                grade=0,
                product="",
                review=review,
                title="",
                status="Error: No content",
                proxy_used=proxy_used
            )

        except Exception as e:
            return Result(
                url=page_num,
                grade=0,
                product="",
                review="",
                title="",
                status=f"Error:{e}",
                proxy_used=proxy_used
            )

    async def process_single_page(self, session, page_num, use_proxy=False):
        """Обработка одной страницы"""
        html, status, proxy_used = await self.fetch_page(session, page_num, use_proxy)
        result = await self.parse_page_content(html, page_num, proxy_used)

        # Добавляем сквозную нумерацию
        with self.lock:
            result.global_number = self.counter
            self.counter += 1
            self.results.append(result)

        print(
            f"[{'PROXY' if proxy_used else 'DIRECT'}] Page {page_num} (Global: {result.global_number}): {result.status}")
        return result

    async def run_direct_connection(self):
        """Запуск парсинга через прямое соединение"""
        print("Starting direct connection parsing...")
        async with aiohttp.ClientSession() as session:
            tasks = []
            for page_num in range(1, self.max_pages + 1):
                task = self.process_single_page(session, page_num, use_proxy=False)
                tasks.append(task)
                # Задержка чтобы не перегружать сервер
                await asyncio.sleep(0.5)

            await asyncio.gather(*tasks, return_exceptions=True)

    async def run_proxy_connection(self):
        """Запуск парсинга через прокси"""
        if not self.proxy_url:
            print("No proxy URL provided, skipping proxy parsing")
            return

        print("Starting proxy connection parsing...")
        async with aiohttp.ClientSession() as session:
            tasks = []
            for page_num in range(1, self.max_pages + 1):
                task = self.process_single_page(session, page_num, use_proxy=True)
                tasks.append(task)
                # Задержка для прокси
                await asyncio.sleep(1)

            await asyncio.gather(*tasks, return_exceptions=True)

    def save_results(self, filename="parsed_results.json"):
        """Сохранение результатов в JSON файл"""
        results_dict = []
        for result in self.results:
            results_dict.append({
                "global_number": result.global_number,
                "page_number": result.page_number,
                "url": result.url,
                "title": result.title,
                "content_preview": result.content_preview,
                "status": result.status,
                "proxy_used": result.proxy_used,
                "timestamp": time.time()
            })

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2, default=str)

        print(f"Results saved to {filename}")

    def save_results_csv(self, filename="parsed_results.csv"):
        """Сохранение результатов в CSV файл"""
        import csv

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Global Number', 'Page Number', 'URL', 'Title', 'Content Preview', 'Status', 'Proxy Used'])

            for result in self.results:
                writer.writerow([
                    result.global_number,
                    result.page_number,
                    result.url,
                    result.title,
                    result.content_preview,
                    result.status,
                    result.proxy_used
                ])

        print(f"Results saved to {filename}")


def run_direct_parser(parser):
    """Функция для запуска в отдельном потоке (прямое соединение)"""
    asyncio.run(parser.run_direct_connection())


def run_proxy_parser(parser):
    """Функция для запуска в отдельном потоке (прокси)"""
    asyncio.run(parser.run_proxy_connection())


async def main():
    # Настройки парсера
    BASE_URL = "https://httpbin.org/html"  # Замените на ваш URL
    MAX_PAGES = 10
    PROXY_URL = "http://your-proxy:port"  # Замените на ваш прокси

    # Создаем парсер
    parser = SiteParser(
        base_url=BASE_URL,
        max_pages=MAX_PAGES,
        use_proxy=True,
        proxy_url=PROXY_URL
    )

    # Запускаем в двух потоках
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=2) as executor:
        # Запускаем оба парсера параллельно
        future_direct = executor.submit(run_direct_parser, parser)
        future_proxy = executor.submit(run_proxy_parser, parser)

        # Ждем завершения
        future_direct.result()
        future_proxy.result()

    end_time = time.time()

    print(f"\nParsing completed in {end_time - start_time:.2f} seconds")
    print(f"Total pages processed: {len(parser.results)}")

    # Сохраняем результаты
    parser.save_results("parsing_results.json")
    parser.save_results_csv("parsing_results.csv")

    # Статистика
    direct_count = sum(1 for r in parser.results if not r.proxy_used)
    proxy_count = sum(1 for r in parser.results if r.proxy_used)
    success_count = sum(1 for r in parser.results if "Success" in r.status)

    print(f"\nStatistics:")
    print(f"Direct connections: {direct_count}")
    print(f"Proxy connections: {proxy_count}")
    print(f"Successful parses: {success_count}")
    print(f"Failed parses: {len(parser.results) - success_count}")


if __name__ == "__main__":
    asyncio.run(main())