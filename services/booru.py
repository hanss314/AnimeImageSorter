import requests
import time


class BImage:
    SFW = False

    def __init__(self, j_token):
        self.char_count = int(j_token['tag_count_character'])
        self.characters_string = str(j_token['tag_string_character'])
        self.characters = self.characters_string.split(' ')

        self.copy_right_count = int(j_token['tag_count_copyright'])
        self.copy_rights_string = str(j_token['tag_string_copyright'])
        self.copy_rights = self.copy_rights_string.split(' ')

        rating = str(j_token['rating'])

        if rating == 's':
            self.SFW = True


class Booru:
    ENDPOINT_MD5 = "https://danbooru.donmai.us/posts.json"
    ENDPOINT_ID = "https://danbooru.donmai.us/posts/"

    @classmethod
    def get(cls, url, params=None, headers=None, retry=2, tries=10):
        r = requests.get(url, params=params, headers=headers)

        if r.status_code != 200:
            ra = int(r.headers.get('Retry-After', retry))
            print(f'[ Sleeping for {ra}s ]', end=' ', flush=True)

            if tries:
                time.sleep(retry)

                return cls.get(url, params=params, headers=headers, tries=tries-1)
            return {}

        return r.json()

    def get_from_md5(self, md5: str) -> dict:
        params = {'limit': '1', 'tags': 'md5:' + md5}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/41.0.2228.0 Safari/537.36Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 ('
                                 'KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}

        return self.get(self.ENDPOINT_MD5, params=params, headers=headers)

    def get_from_id(self, id_: int) -> dict:
        r = requests.get(self.ENDPOINT_ID + str(id_) + '.json')
        try:
            return r.json()
        except Exception:
            print(r.text)
            return None
