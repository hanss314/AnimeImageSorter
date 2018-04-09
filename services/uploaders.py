import requests
import base64
import time

from .prompts import *


class Uploader:
    KEY_FILE = None

    def __init__(self):
        if self.KEY_FILE is None:
            print(f'\n{ERROR_PROMPT}KEY_FILE not defined for custom uploader. Aborting.')
            quit()

        try:
            with open(self.KEY_FILE) as file_:
                self.api_key = file_.read()
        except FileNotFoundError:
            print(f'\n{ERROR_PROMPT}{self.KEY_FILE} missing.')
            print(MINOR_PROMPT + 'To fix this problem check GitHub.')
            quit()

    def upload(self, path: str) -> str:
        raise NotImplementedError


class ImgurResult:
    def __init__(self, url: str, user_rate: int, client_rate: int,
                 post_remaining: int, user_reset: int, post_reset: int):
        self.url = url
        self.user_rate = user_rate
        self.client_rate = client_rate
        self.post_remaining = post_remaining
        self.user_reset = user_reset
        self.post_reset = post_reset


class Imgur(Uploader):
    ENDPOINT = 'https://api.imgur.com/3/upload'
    KEY_FILE = 'keys/imgurApiKey.txt'
    NAME = 'Imgur'

    def __init__(self):
        super().__init__()

        self.last_image = None

    def upload(self, path: str) -> str:
        headers = {
            'Authorization': 'Client-ID ' + self.api_key
        }
        with open(path, 'rb') as file_:
            files = {'image': base64.b64encode(file_.read())}

        r = requests.post(self.ENDPOINT, data=files, headers=headers)

        json = r.json()

        url = json['data'].get('link', '')
        user_remaining = int(r.headers.get('X-RateLimit-UserRemaining', 100))
        client_remaining = int(r.headers.get('X-RateLimit-ClientRemaining', 100))
        post_remaining = int(r.headers.get('X-Post-Rate-Limit-Remaining', 100))
        user_reset = int(r.headers.get('X-RateLimit-UserReset', 0))
        post_reset = int(r.headers.get('X-Post-Rate-Limit-Reset', 0))

        if self.last_image is not None:
            # Handle rate limits
            if self.last_image.user_rate < 15:
                print(f'\n{ERROR_PROMPT}Too many Imgur uploads. Approaching user rate limit of x per hour. '
                      f'Waiting until user rate is reset at: {self.last_image.user_reset}')
                time.sleep(self.last_image.user_reset - time.time())
            if self.last_image.client_rate < 15:
                print(f'\n{ERROR_PROMPT}Too many Imgur uploads. Approaching client rate limit of 1,250 per '
                      f'day. Try again in 24hrs.')
                quit()
            if self.last_image.post_remaining < 15:
                print(f'\n{ERROR_PROMPT}Too many Imgur uploads. Approaching post rate limit of 1,250 per '
                      f'hour. Waiting until user rate is reset in: {self.last_image.post_reset} seconds.')
                time.sleep(self.last_image.post_reset)

        self.last_image = ImgurResult(url, user_remaining, client_remaining, post_remaining, user_reset, post_reset)

        return url


class NoLife(Uploader):
    ENDPOINT = 'https://botter.doesnt-have-a.life/upload.php'
    KEY_FILE = 'keys/noLifeKey.txt'
    NAME = 'NoLife'

    def upload(self, path: str) -> str:
        arguments = {'secret': self.api_key}
        with open(path, 'rb') as file_:
            files = {'sharex': file_}

            r = requests.post(self.ENDPOINT, files=files, data=arguments)

        return r.text
