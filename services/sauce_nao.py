import requests
import time
import os


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

    def __init__(self, api_key: str):
        self.api_key = api_key

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
        params = {'db': '999', 'output_type': '2',
                  'numres': '16', 'api_key': self.api_key, 'url': url}

        r = self.get(self.ENDPOINT, params=params)

        try:
            return SauceNaoResult(r.json())
        except Exception:
            print('\n==> Invalid result.')
            return SauceNaoResult({})


if __name__ == '__main__':
    print(SauceNao(open('sauceNaoApiKey.txt').read()).request('https://i.imgur.com/o7JmR2k.jpg'))
