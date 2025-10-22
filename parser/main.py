import json
import time

from bs4 import BeautifulSoup as bs
import requests


urls = ["https://www.banki.ru/services/responses/list/product/debitcards",
        # "https://www.banki.ru/services/responses/list/product/creditcards",
        # "https://www.banki.ru/services/responses/list/product/hypothec",
        # "https://www.banki.ru/services/responses/list/product/autocredits",
        # "https://www.banki.ru/services/responses/list/product/credits",
        # "https://www.banki.ru/services/responses/list/product/restructing",
        # "https://www.banki.ru/services/responses/list/product/deposits",
        # "https://www.banki.ru/services/responses/list/product/transfers",
        # "https://www.banki.ru/services/responses/list/product/remote"
        ]

root = "https://www.banki.ru"

for url in urls:
    i = 1
    page = requests.get(url)
    print(page.status_code)
    name = url.split("/")[-1]
    with open(f'data/{name}.json', 'a+', encoding="utf-8") as file:
        # while page.status_code == 200:

        content = page.text
        soup = bs(content)
        allfd = soup.find_all('article', class_="responses__response")
        with open("data/test.txt", 'a', encoding='utf-8') as f:
            f.write(content)
            f.write("----------------------------------")

            # links = []
            # for href in allfd:
            #     links.append(href.find('a', href=True)['href'])
            #
            # for link in links:
            #     result = requests.get(f'{root}{link}')
            #     if page.status_code == 200:
            #         time.sleep(1)
            #         content = result.text
            #         soup = bs(content, 'lxml')
            #         fd = soup.find('div',class_='article-text response-page__text markup-inside-small markup-inside-small--bullet').get_text(strip=True, separator=' ')
            #         title = soup.find('h1').get_text(strip=True, separator=' ')
            #         json.dump({'title': title, 'review': fd}, file, ensure_ascii=False, indent=4)
            #     i += 1
            #     page = requests.get(f'https://www.banki.ru/investment/responses/list?page={i}&isMobile=0')
            #