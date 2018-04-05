import hashlib
import time
import os
import re

from shutil import copyfile

from services.booru import Booru, BImage
from services.sauce_nao import SauceNao
from services.no_life import NoLife
from services.imgur import Imgur


class Program:
    SERIES = 1
    CHARACTER = 2

    MOVE = 1
    COPY = 2

    HARD = 0
    SOFT = 1

    COPIES = 0
    MIXED = 1
    FIRST = 2
    SKIP = 3

    IMGUR = 0
    NOLIFE = 1

    # Regex used to find MD5 in filenames
    md5_regex = re.compile('^[0-9a-f]{32}$')

    def __init__(self):
        self.multiple_operation = self.SKIP
        self.base_directory = os.getcwd()
        self.file_operation = self.MOVE
        self.do_reverse_image = False
        self.image_host = self.IMGUR
        self.md5_option = self.SOFT
        self.sort_by = self.SERIES

        self.get_settings()

        if self.do_reverse_image:
            # SauceNao and Imgur Stuff
            self.remaining_sauces = 2 ** 16
            self.remaining_sauces_long = 2 ** 16
            self.last_image = None

            if os.path.exists('keys/sauceNaoApiKey.txt'):
                with open('keys/sauceNaoApiKey.txt') as file_:
                    self.sauce_nao_api_key = file_.read()
            else:
                print('\n==> keys/sauceNaoApiKey.txt missing.')
                print('==> To fix this problem check GitHub.')
                return

            key_file = 'keys/imgurApiKey.txt' if self.image_host == self.IMGUR else 'keys/noLifeKey.txt'

            if os.path.exists(key_file):
                with open(key_file) as file_:
                    self.image_host_key = file_.read()
            else:
                print(f'\n==> {key_file} missing.')
                print('==> To fix this problem check GitHub.')
                return

        # List all files in the current folder
        files = [
            i for i in os.listdir(self.base_directory)
            if i[-4:].lower() in ['.jpg', '.png', '.gif']
        ]
        print(f'\n==> Found {len(files)} images.')

        for file_ in files:
            filename = file_[::-1].split('.', 1)[1][::-1]
            filename_long = file_
            file_ = os.path.join(self.base_directory, file_)

            print(f'\n==> Operating on {file_}')
            md5 = self.get_md5(file_, filename)

            print(f'==> Searching Danbooru for {md5}..', end=' ', flush=True)
            danbooru_result = Booru().get_from_md5(md5)

            if self.do_reverse_image and not danbooru_result:
                print('[ Not found ]')

                # Ratelimits
                if self.remaining_sauces < 2:
                    print('\n==> Too many Sauces, approaching SauceNao 20 requests per 30s limit. Waiting 30s.')
                    time.sleep(30)
                if self.remaining_sauces_long < 2:
                    print(
                        '\n==> Too many Sauces, approaching SauceNao 300 requests per 24hrs limit. Monitor your usage '
                        'at https://saucenao.com/user.php?page=search-usage and start again.')
                    return
                if self.image_host == self.IMGUR and self.last_image is not None:
                    if self.last_image.user_rate < 15:
                        print(
                            '\n==> Too many Imgur uploads. Approaching user rate limit of x per hour. Waiting until '
                            'user rate is reset at: ' + self.last_image.user_reset)
                        time.sleep(self.last_image.user_reset - time.time())
                    if self.last_image.client_rate < 15:
                        print(
                            '\n==> Too many Imgur uploads. Approaching client rate limit of 1,250 per day. Try again '
                            'in 24hrs.')
                        return
                    if self.last_image.post_remaining < 15:
                        print(f'\n==> Too many Imgur uploads. Approaching post rate limit of 1,250 per hour. Waiting '
                              f'until user rate is reset in: {self.last_image.post_reset} seconds.')
                        time.sleep(self.last_image.post_reset)

                # Upload image to chosen host
                if self.image_host == self.IMGUR:
                    print('==> Uploading to Imgur for reverse image search..', end=' ', flush=True)
                    self.last_image = image = Imgur.upload(file_, self.image_host_key)
                    if image.url:
                        print(f'[ {str(min(image.client_rate, min(image.user_rate, image.post_remaining)))} credits '
                              f'left ]')
                        url = image.url
                    else:
                        print('[ Failed ]')
                        print('==> File could not be identified.')
                        continue
                elif self.image_host == self.NOLIFE:
                    print('==> Uploading to NoLife for reverse image search..', end=' ', flush=True)
                    url = NoLife.upload(file_, self.image_host_key)
                    print(f'[ Okay ]')
                else:
                    print('\n==> Unknown image host.')
                    return

                # Reverse image search
                print(f'==> Searching SauceNao with {url}..', end=' ', flush=True)
                response = SauceNao(self.sauce_nao_api_key).request(url)
                results = response.results
                self.remaining_sauces = int(response.header['short_remaining'])
                self.remaining_sauces_long = int(response.header['long_remaining'])

                # Remove all low similarity results
                for header, data in results:
                    if float(header['similarity']) < 90.0:
                        results.remove((header, data))

                # Get danbooru id, if any high similarity result has one, then get danbooru post from it
                if any('danbooru_id' in x for _, x in results):
                    print(f'[ Okay ({self.remaining_sauces} remaining) ]')
                    danbooru_id = [i['danbooru_id'] for _, i in results if 'danbooru_id' in i][0]

                    danbooru_result = Booru().get_from_id(danbooru_id)
                else:
                    print(f'[ Not found ({self.remaining_sauces} remaining) ]')
            elif danbooru_result:
                print('[ Okay ]')
                danbooru_result = danbooru_result[0]
            else:
                print('[ Not found ]')

            if danbooru_result:
                b_image = BImage(danbooru_result)

                if (b_image.char_count >= 1 and self.sort_by == self.CHARACTER) or \
                        (b_image.copy_right_count >= 1 and self.sort_by == self.SERIES):
                    self.copy_move_file(file_, filename_long, b_image)
            else:
                print('==> File could not be identified.')

        print('\n==> All Operations finished')

    def get_settings(self) -> None:
        print('==> Enter image directory:')
        print('==> --------------------------------------------------')
        directory = input('==> ').strip()

        if directory and not os.path.exists(directory):
            print(f'{directory} is not a valid directory.')
            return
        self.base_directory = directory or os.getcwd()

        print(f'\nDirectory "{self.base_directory}" selected.')

        print('\n==> Sort by:')
        print('==> [S]eries   [C]haracters   [Q]uit')
        print('==> --------------------------------------------------')
        key = (input('==> ') or 'Q')[0].upper()
        self.sort_by = {'S': self.SERIES, 'C': self.CHARACTER}.get(key)
        if self.sort_by is None:
            return

        print(f'\n==> File processing manner:')
        print('==> [M]ove   [C]opy   [Q]uit')
        print('==> --------------------------------------------------')
        key = (input('==> ') or 'Q')[0].upper()
        self.file_operation = {'M': self.MOVE, 'C': self.COPY}.get(key)
        if self.file_operation is None:
            return

        print('\n==> Hash calculation:')
        print('==>  Hard always uses file-hashes.')
        print('==>   Lower success rate and speed but no false positives.')
        print('==>  Soft first looks for hashes in filenames.')
        print('==>   faster and better success rate, but may have false positives.')
        print('==> [H]ard   [S]oft   [Q]uit')
        print('==> --------------------------------------------------')
        key = (input('==> ') or 'Q')[0].upper()
        self.md5_option = {'H': self.HARD, 'S': self.SOFT}.get(key)
        if self.md5_option is None:
            return

        print('\n==> Multiple tags/characters/series in the same image:')
        print('==> [C]copies   [M]ixed names   [F]irst   [S]kip   [Q]uit')
        print('==> --------------------------------------------------')
        key = (input('==> ') or 'Q')[0].upper()
        self.multiple_operation = {'C': self.COPIES, 'M': self.MIXED, 'F': self.FIRST, 'S': self.SKIP}.get(key)
        if self.multiple_operation is None:
            return

        print('\n==> Reverse image search images not found through hashing:')
        print('==> [Y]es   [N]o   [Q]uit')
        print('==> --------------------------------------------------')
        key = (input('==> ') or 'Q')[0].upper()
        self.do_reverse_image = {'Y': True, 'N': False}.get(key)
        if self.do_reverse_image is None:
            return

        if self.do_reverse_image:
            print('\n==> Image host:')
            print('==> [I]mgur   [N]oLife   [Q]uit')
            print('==> --------------------------------------------------')
            key = (input('==> ') or 'Q')[0].upper()
            self.image_host = {'I': self.IMGUR, 'N': self.NOLIFE}.get(key)
            if self.image_host is None:
                return

    def get_md5(self, file_: str, filename: str) -> str:
        # improves speed, may reduce accuracy, when a file has a name that could be its MD5 hash, but isn't
        if self.md5_option == self.SOFT and self.md5_regex.match(filename):
            return filename
        else:
            return self.calculate_md5(file_)

    @staticmethod
    def calculate_md5(filename: str) -> str:
        with open(filename, 'rb') as file_:
            hsh = hashlib.md5(file_.read())
        return hsh.hexdigest().lower()

    def copy_move_file(self, file_: str, filename: str, b_image: BImage) -> None:
        target_folders = []

        if self.multiple_operation == self.COPIES:
            if self.sort_by == self.CHARACTER:
                target_folders += b_image.characters
            else:
                target_folders += b_image.copy_rights
        elif self.multiple_operation == self.MIXED:
            if self.sort_by == self.CHARACTER:
                target_folders.append(b_image.characters_string)
            else:
                target_folders.append(b_image.copy_rights_string)
        elif self.multiple_operation == self.FIRST:
            if self.sort_by == self.CHARACTER:
                target_folders.append(b_image.characters[0])
            else:
                target_folders.append(b_image.copy_rights[0])
        else:
            if self.sort_by == self.CHARACTER:
                if len(b_image.characters) > 1:
                    return
                target_folders.append(b_image.characters[0])
            else:
                if len(b_image.copy_rights) > 1:
                    return
                target_folders.append(b_image.copy_rights[0])

        # CopyMove File in target folder(s)
        for n, target_folder in enumerate(target_folders):
            target_file = os.path.join(self.base_directory, target_folder, filename)
            target_folder = os.path.dirname(target_file)

            if not os.path.exists(target_folder):
                os.makedirs(target_folder)

            if self.file_operation == self.COPY:
                print(f'==> Copying to {target_folder}')
                copyfile(file_, target_file)
            elif self.file_operation == self.MOVE:
                print(f'==> Moving to {target_folder}')
                if n == len(target_folders) - 1:
                    if os.path.exists(target_file):
                        os.remove(target_file)
                    os.rename(file_, target_file)
                else:
                    copyfile(file_, target_file)


if __name__ == '__main__':
    Program()
