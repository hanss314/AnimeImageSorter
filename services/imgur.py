import requests
import base64


class ImgurResult:
    def __init__(self, url: str, user_rate: int, client_rate: int,
                 post_remaining: int, user_reset: int, post_reset: int):
        self.url = url
        self.user_rate = user_rate
        self.client_rate = client_rate
        self.post_remaining = post_remaining
        self.user_reset = user_reset
        self.post_reset = post_reset


class Imgur:
    ENDPOINT = 'https://api.imgur.com/3/upload'

    @classmethod
    def upload(cls, path: str, api_key: str) -> ImgurResult:
        headers = {
            'Authorization': 'Client-ID ' + api_key
        }
        with open(path, 'rb') as file_:
            files = {'image': base64.b64encode(file_.read())}

        r = requests.post(cls.ENDPOINT, data=files, headers=headers)
        print(r, end=' ', flush=True)

        json = r.json()

        url = json['data'].get('link', '')
        user_remaining = int(r.headers.get('X-RateLimit-UserRemaining', 100))
        client_remaining = int(r.headers.get('X-RateLimit-ClientRemaining', 100))
        post_remaining = int(r.headers.get('X-Post-Rate-Limit-Remaining', 100))
        user_reset = int(r.headers.get('X-RateLimit-UserReset', 0))
        post_reset = int(r.headers.get('X-Post-Rate-Limit-Reset', 0))

        return ImgurResult(url, user_remaining, client_remaining,
                           post_remaining, user_reset, post_reset)


if __name__ == '__main__':
    Imgur().upload('../../../ReZero/WgwcpHH.png', 'f46352c2723d01a')
