import argparse
import hashlib
import time
import sys
import os
import re

from shutil import copyfile

from services.booru import Booru, BImage
from services.sauce_nao import SauceNao
from services.no_life import NoLife
from services.imgur import Imgur


class Program:
    if sys.stdout.isatty() and os.name != 'nt':
        PREAMBLE_PROMPT = '\033[1;33m==> \033[1;37m'
        PREAMBLE_SUB = '\033[1;33m:: \033[0;37m'
        INPUT_PROMPT = '\033[1;33m-> \033[0;37m'
        MAJOR_PROMPT = '\033[1;32m==> \033[1;37m'
        MINOR_PROMPT = '\033[1;34m  -> \033[1;37m'
        ERROR_PROMPT = '\033[1;32m:: \033[0;37m'
        NORMAL = '\033[0;37m'
        BOLD = '\033[1;37m'
    else:  # Windows or pipe compatibility
        PREAMBLE_PROMPT = '==> '
        PREAMBLE_SUB = ':: '
        INPUT_PROMPT = '-> '
        MAJOR_PROMPT = '==> '
        MINOR_PROMPT = '  -> '
        ERROR_PROMPT = ':: '
        NORMAL = ''
        BOLD = ''

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
        self.multiple_operation = None
        self.base_directory = None
        self.file_operation = None
        self.do_reverse_image = None
        self.image_host = None
        self.md5_option = None
        self.sort_by = None

        parser = argparse.ArgumentParser(description='Sort large amount of anime pictures.')
        parser.add_argument('--dir', default=None, nargs=1, help='Where to search for images')
        parser.add_argument('--sort-by', default=None, nargs=1, help='What to group images by')
        parser.add_argument('--file-op', default=None, nargs=1, help='How to process files')
        parser.add_argument('--md5', default=None, nargs=1, help='MD5 calculation process')
        parser.add_argument('--multiple', default=None, nargs=1, help='How to handle multiple tags')
        parser.add_argument('--do-reverse', default=None, nargs=1, help='Whether to reverse image search')
        parser.add_argument('--host', default=None, nargs=1, help='Where to upload images')
        args = parser.parse_args(sys.argv[1:])

        self.multiple_operation = {'copies': self.COPIES, 'mixed': self.MIXED, 'first': self.FIRST, 'skip': self.SKIP}.get(args.multiple[0])
        self.sort_by = {'series': self.SERIES, 'character': self.CHARACTER}.get(args.sort_by[0])
        self.file_operation = {'move': self.MOVE, 'copy': self.COPY}.get(args.file_op[0])
        self.image_host = {'imgur': self.IMGUR, 'nolife': self.NOLIFE}.get(args.host[0])
        self.do_reverse_image = {'true': True, 'false': False}.get(args.do_reverse[0])
        self.md5_option = {'hard': self.HARD, 'soft': self.SOFT}.get(args.md5[0])
        self.base_directory = args.dir[0]

        self.unknown = []
        if os.path.exists('unknown.txt'):
            with open('unknown.txt') as file_:
                self.unknown = file_.read().split('\n')

        if not self.get_settings():
            return

        if self.do_reverse_image:
            # SauceNao and Imgur Stuff
            self.remaining_sauces = 2 ** 16
            self.remaining_sauces_long = 2 ** 16
            self.last_image = None

            if os.path.exists('keys/sauceNaoApiKey.txt'):
                with open('keys/sauceNaoApiKey.txt') as file_:
                    self.sauce_nao_api_key = file_.read()
            else:
                print(f'\n{self.MAJOR_PROMPT}keys/sauceNaoApiKey.txt missing.')
                print(self.MINOR_PROMPT + 'To fix this problem check GitHub.')
                return

            key_file = 'keys/imgurApiKey.txt' if self.image_host == self.IMGUR else 'keys/noLifeKey.txt'

            if os.path.exists(key_file):
                with open(key_file) as file_:
                    self.image_host_key = file_.read()
            else:
                print(f'\n{self.MAJOR_PROMPT}{key_file} missing.')
                print(self.MINOR_PROMPT + 'To fix this problem check GitHub.')
                return

        # List all files in the current folder
        files = [
            i for i in os.listdir(self.base_directory)
            if i[-4:].lower() in ['.jpg', '.png', '.gif']
        ]
        print(f'{self.MAJOR_PROMPT}Found {len(files)} images.')

        for file_ in files:
            filename = file_[::-1].split('.', 1)[1][::-1]
            filename_long = file_
            file_ = os.path.join(self.base_directory, file_)

            print(f'\n{self.MAJOR_PROMPT}Operating on {file_}')

            if file_ in self.unknown:
                print(self.ERROR_PROMPT + 'Previously marked as unknown. Skipping.')
                continue

            md5 = self.get_md5(file_, filename)

            print(f'{self.MINOR_PROMPT}Searching Danbooru for {md5}..{self.NORMAL}', end=' ', flush=True)
            danbooru_result = Booru().get_from_md5(md5)

            if self.do_reverse_image and not danbooru_result:
                print('[ Not found ]')

                # Ratelimits
                if self.remaining_sauces < 2:
                    print(f'\n{self.ERROR_PROMPT}Too many Sauces, approaching SauceNao 20 requests per 30s limit.'
                          f'Waiting 30s.')
                    time.sleep(30)
                if self.remaining_sauces_long < 2:
                    print(f'\n{self.ERROR_PROMPT}Too many Sauces, approaching SauceNao 300 requests per 24hrs limit.'
                          f'Monitor your usage at https://saucenao.com/user.php?page=search-usage and start again.')
                    return
                if self.image_host == self.IMGUR and self.last_image is not None:
                    if self.last_image.user_rate < 15:
                        print(f'\n{self.ERROR_PROMPT}Too many Imgur uploads. Approaching user rate limit of x per hour.'
                              f'Waiting until user rate is reset at: ' + self.last_image.user_reset)
                        time.sleep(self.last_image.user_reset - time.time())
                    if self.last_image.client_rate < 15:
                        print(f'\n{self.ERROR_PROMPT}Too many Imgur uploads. Approaching client rate limit of 1,250 per'
                              f'day. Try again in 24hrs.')
                        return
                    if self.last_image.post_remaining < 15:
                        print(f'\n{self.ERROR_PROMPT}Too many Imgur uploads. Approaching post rate limit of 1,250 per'
                              f'hour. Waiting until user rate is reset in: {self.last_image.post_reset} seconds.')
                        time.sleep(self.last_image.post_reset)

                # Upload image to chosen host
                if self.image_host == self.IMGUR:
                    print(self.MINOR_PROMPT + 'Uploading to Imgur for reverse image search..', end=' ', flush=True)
                    print(self.NORMAL, end='')
                    self.last_image = image = Imgur.upload(file_, self.image_host_key)
                    if image.url:
                        print(f'[ {str(min(image.client_rate, min(image.user_rate, image.post_remaining)))} credits '
                              f'left ]')
                        url = image.url
                    else:
                        print('[ Failed ]')
                        self.mark_unknown(file_)
                        print(self.ERROR_PROMPT + 'File could not be identified.')
                        continue
                elif self.image_host == self.NOLIFE:
                    print(self.MINOR_PROMPT + 'Uploading to NoLife for reverse image search..', end=' ', flush=True)
                    print(self.NORMAL, end='')
                    url = NoLife.upload(file_, self.image_host_key)
                    print('[ Okay ]')
                else:
                    print(f'\n{self.MAJOR_PROMPT}Unknown image host.')
                    return

                # Reverse image search
                print(f'{self.MINOR_PROMPT}Searching SauceNao with {url}..{self.NORMAL}', end=' ', flush=True)
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
                self.mark_unknown(file_)
                print(self.ERROR_PROMPT + 'File could not be identified.')

        print(f'\n{self.MAJOR_PROMPT}All Operations finished')

    def mark_unknown(self, path: str) -> None:
        self.unknown.append(path)
        with open('unknown.txt', 'w') as file_:
            file_.write('\n'.join(self.unknown))

    def get_settings(self) -> bool:
        if self.base_directory is None:
            print(self.PREAMBLE_PROMPT + 'Enter image directory:')
            directory = input(self.INPUT_PROMPT).strip()

            if directory and not os.path.exists(directory):
                print(f'{directory} is not a valid directory.')
                return False
            self.base_directory = directory or os.getcwd()
        print(f'\n{self.BOLD}Directory "{self.base_directory}" selected.\n')
        if self.sort_by is None:
            print(self.PREAMBLE_PROMPT + 'Sort by:')
            print(self.PREAMBLE_PROMPT + '[S]eries   [C]haracters   [Q]uit')
            key = (input(self.INPUT_PROMPT) or 'Q')[0].upper()
            self.sort_by = {'S': self.SERIES, 'C': self.CHARACTER}.get(key)
            if self.sort_by is None:
                return False
            print()
        if self.file_operation is None:
            print(f'{self.PREAMBLE_PROMPT}File processing manner:')
            print(self.PREAMBLE_PROMPT + '[M]ove   [C]opy   [Q]uit')
            key = (input(self.INPUT_PROMPT) or 'Q')[0].upper()
            self.file_operation = {'M': self.MOVE, 'C': self.COPY}.get(key)
            if self.file_operation is None:
                return False
            print()
        if self.md5_option is None:
            print(f'{self.PREAMBLE_PROMPT}Hash calculation:')
            print(self.PREAMBLE_SUB + ' Hard always uses file-hashes.')
            print(self.PREAMBLE_SUB + '  Lower success rate and speed but no false positives.')
            print(self.PREAMBLE_SUB + ' Soft first looks for hashes in filenames.')
            print(self.PREAMBLE_SUB + '  Faster and better success rate, but may have false positives.')
            print(self.PREAMBLE_PROMPT + '[H]ard   [S]oft   [Q]uit')
            key = (input(self.INPUT_PROMPT) or 'Q')[0].upper()
            self.md5_option = {'H': self.HARD, 'S': self.SOFT}.get(key)
            if self.md5_option is None:
                return False
            print()
        if self.multiple_operation is None:
            print(f'{self.PREAMBLE_PROMPT}Multiple tags/characters/series in the same image:')
            print(self.PREAMBLE_PROMPT + '[C]copies   [M]ixed names   [F]irst   [S]kip   [Q]uit')
            key = (input(self.INPUT_PROMPT) or 'Q')[0].upper()
            self.multiple_operation = {'C': self.COPIES, 'M': self.MIXED, 'F': self.FIRST, 'S': self.SKIP}.get(key)
            if self.multiple_operation is None:
                return False
            print()
        if self.do_reverse_image is None:
            print(f'{self.PREAMBLE_PROMPT}Reverse image search images not found through hashing:')
            print(self.PREAMBLE_PROMPT + '[Y]es   [N]o   [Q]uit')
            key = (input(self.INPUT_PROMPT) or 'Q')[0].upper()
            self.do_reverse_image = {'Y': True, 'N': False}.get(key)
            if self.do_reverse_image is None:
                return False
            print()
        if self.image_host is None and self.do_reverse_image:
            print(f'{self.PREAMBLE_PROMPT}Image host:')
            print(self.PREAMBLE_PROMPT + '[I]mgur   [N]oLife   [Q]uit')
            key = (input(self.INPUT_PROMPT) or 'Q')[0].upper()
            self.image_host = {'I': self.IMGUR, 'N': self.NOLIFE}.get(key)
            if self.image_host is None:
                return False
            print()

        return True

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
                print(self.MINOR_PROMPT + f'Copying to {target_folder}')
                copyfile(file_, target_file)
            elif self.file_operation == self.MOVE:
                print(self.MINOR_PROMPT + f'Moving to {target_folder}')
                if n == len(target_folders) - 1:
                    if os.path.exists(target_file):
                        os.remove(target_file)
                    os.rename(file_, target_file)
                else:
                    copyfile(file_, target_file)


if __name__ == '__main__':
    Program()
