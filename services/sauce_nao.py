import requests
import time


class SauceNaoResult:
    def __init__(self, response: dict):
        self.header = response.get('header', [])
        self.results = []

        for result in response['results']:
            self.results.append((result['header'], result['data']))


class SauceNao:
    ENDPOINT = 'https://saucenao.com/search.php'

    def __init__(self, api_key: str):
        self.api_key = api_key

    @classmethod
    def get(cls, url, params=None, retry=240):
        r = requests.get(url, params=params)
        print(r, end=' ', flush=True)

        if r.status_code == 429:
            ra = int(r.headers.get('Retry-After', retry))
            print(f'[ {ra}s ]', end=' ', flush=True)
            time.sleep(ra)
            ra *= 2

            return cls.get(url, params=params, retry=ra)

        return r

    def request(self, url: str) -> SauceNaoResult:
        params = {'db': '999', 'output_type': '2',
                  'numres': '16', 'api_key': self.api_key, 'url': url}

        r = self.get(self.ENDPOINT, params=params)

        return SauceNaoResult(r.json())


if __name__ == '__main__':
    print(SauceNao(open('sauceNaoApiKey.txt').read()).request('https://i.imgur.com/o7JmR2k.jpg'))
