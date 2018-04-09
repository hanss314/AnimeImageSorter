import requests
import time

from .prompts import *


proxies = {'https': open('keys/proxy.txt').read()} if os.path.exists('keys/proxy.txt') else {}


class SauceNaoResult:
    def __init__(self, response: dict):
        self.header = response.get('header', {
            'short_remaining': 50,
            'long_remaining': 50
        })
        self.results = []

        for result in response.get('results', []):
            self.results.append((result['header'], result['data']))


class SauceNao:
    ENDPOINT = 'https://saucenao.com/search.php'
    KEY_FILE = 'keys/sauceNaoApiKey.txt'

    def __init__(self):
        self.remaining_sauces = 2 ** 16
        self.remaining_sauces_long = 2 ** 16

        try:
            with open(self.KEY_FILE) as file_:
                self.api_key = file_.read()
        except FileNotFoundError:
            print(f'\n{MAJOR_PROMPT}SauceNao API key missing. Aborting.')
            quit()

    @classmethod
    def get(cls, url, params=None, retry=240):
        r = requests.get(url, proxies=proxies, params=params)

        if r.status_code == 429:
            ra = int(r.headers.get('Retry-After', retry))
            print(f'[ Sleeping for {ra}s ]', end=' ', flush=True)
            time.sleep(ra)
            ra *= 2

            return cls.get(url, params=params, retry=ra)

        return r

    def request(self, url: str) -> SauceNaoResult:
        # Ratelimits
        if self.remaining_sauces < 2:
            print(f'\n{ERROR_PROMPT}Too many Sauces, approaching SauceNao 20 requests per 30s limit.'
                  f'Waiting 30s.')
            time.sleep(30)
        if self.remaining_sauces_long < 2:
            print(f'\n{ERROR_PROMPT}Too many Sauces, approaching SauceNao 300 requests per 24hrs limit.'
                  f'Monitor your usage at https://saucenao.com/user.php?page=search-usage and start again.')
            quit()

        params = {'db': '999', 'output_type': '2',
                  'numres': '16', 'api_key': self.api_key, 'url': url}

        r = self.get(self.ENDPOINT, params=params)

        try:
            rtn = SauceNaoResult(r.json())
        except requests.exceptions.RequestException:
            print('\n{ERROR_PROMPT}Invalid result.')
            rtn = SauceNaoResult({})

        self.remaining_sauces = int(rtn.header['short_remaining'])
        self.remaining_sauces_long = int(rtn.header['long_remaining'])

        return rtn
