import requests


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

    def request(self, url: str) -> SauceNaoResult:
        params = {'db': '999', 'output_type': '2',
                  'numres': '16', 'api_key': self.api_key, 'url': url}

        r = requests.get(self.ENDPOINT, params=params)
        return SauceNaoResult(r.json())


if __name__ == '__main__':
    print(SauceNao(open('sauceNaoApiKey.txt').read()).request('https://i.imgur.com/o7JmR2k.jpg'))
