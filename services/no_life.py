import requests


class NoLife:
    ENDPOINT = 'https://botter.doesnt-have-a.life/upload.php'

    @classmethod
    def upload(cls, path: str, secret: str) -> str:
        arguments = {'secret': secret}
        with open(path, 'rb') as file_:
            files = {'sharex': file_}

            r = requests.post(cls.ENDPOINT, files=files, data=arguments)

        return r.text
