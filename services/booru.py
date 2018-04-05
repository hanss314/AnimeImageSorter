import requests


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

    def get_from_md5(self, md5: str) -> dict:
        params = {'limit': '1', 'tags': 'md5: ' + md5}

        r = requests.get(self.ENDPOINT_MD5, params=params)
        return r.json()

    def get_from_id(self, id_: int) -> dict:
        r = requests.get(self.ENDPOINT_ID + str(id_) + '.json')
        return r.json()
