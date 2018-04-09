import argparse
import hashlib
import time
import sys
import os
import re

from shutil import copyfile

from services.booru import Booru, BImage
from services.sauce_nao import SauceNao
from services.uploaders import NoLife, Imgur

from services.prompts import *


class Program:
    SERIES = 'Series'
    CHARACTER = 'Character'
    BOTH = 'Both'

    MOVE = 'Move'
    COPY = 'Copy'

    HARD = 'Hard'
    SOFT = 'Soft'

    COPIES = 'Copies'
    MIXED = 'Mixed Names'
    FIRST = 'First'
    SKIP = 'Skip'

    IMGUR = 'Imgur'
    NOLIFE = 'NoLife'

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
        parser.add_argument('--dir', default=[None], nargs=1, help='Where to search for images')
        parser.add_argument('--sort-by', default=[None], nargs=1, help='What to group images by')
        parser.add_argument('--file-op', default=[None], nargs=1, help='How to process files')
        parser.add_argument('--md5', default=[None], nargs=1, help='MD5 calculation process')
        parser.add_argument('--multiple', default=[None], nargs=1, help='How to handle multiple tags')
        parser.add_argument('--do-reverse', default=[None], nargs=1, help='Whether to reverse image search')
        parser.add_argument('--host', default=[None], nargs=1, help='Where to upload images')
        args = parser.parse_args(sys.argv[1:])

        self.multiple_operation = {'copies': self.COPIES, 'mixed': self.MIXED, 'first': self.FIRST, 'skip': self.SKIP}.get(args.multiple[0])
        self.sort_by = {'series': self.SERIES, 'character': self.CHARACTER, 'both': self.BOTH}.get(args.sort_by[0])
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
            self.sauce_nao = SauceNao()

            if self.image_host == self.IMGUR:
                self.image_host = Imgur()
            elif self.image_host == self.NOLIFE:
                self.image_host = NoLife()
            else:
                print(f'{ERROR_PROMPT}Unknown image host. Aborting.')
                return

        # List all files in the current folder
        files = [
            i for i in os.listdir(self.base_directory)
            if i[-4:].lower() in ['.jpg', '.png', '.gif']
        ]
        print(f'{MAJOR_PROMPT}Found {len(files)} images.')

        skipped = 0
        for file_ in files:
            filename = file_[::-1].split('.', 1)[1][::-1]
            filename_long = file_
            file_ = os.path.join(self.base_directory, file_)

            if file_ in self.unknown:
                skipped += 1
                continue
            print()
            if skipped:
                print(f'{ERROR_PROMPT}Skipped {skipped} images previously marked as unknown.')
                skipped = 0

            print(f'{MAJOR_PROMPT}Operating on {file_}')

            md5 = self.get_md5(file_, str(filename))

            print(f'{MINOR_PROMPT}Searching Danbooru for {md5}..{NORMAL}', end=' ', flush=True)
            danbooru_result = Booru().get_from_md5(md5)

            if self.do_reverse_image and not danbooru_result:
                print(NOT_FOUND)

                # Upload image to chosen host
                print(f'{MINOR_PROMPT}Uploading to {self.image_host.NAME} for reverse image search..{NORMAL}',
                      end=' ', flush=True)
                url = self.image_host.upload(file_)
                if not url:
                    print('[Failed]')
                    self.mark_unknown(file_)
                    print(ERROR_PROMPT + 'File could not be identified.')
                    continue
                else:
                    print('')

                # Reverse image search
                print(f'{MINOR_PROMPT}Searching SauceNao with {url}..{NORMAL}', end=' ', flush=True)
                response = self.sauce_nao.request(url)
                results = response.results

                # Remove all low similarity results
                for header, data in results:
                    if float(header['similarity']) < 90.0:
                        results.remove((header, data))

                # Get danbooru id, if any high similarity result has one, then get danbooru post from it
                if any('danbooru_id' in x for _, x in results):
                    print(OKAY)
                    danbooru_id = [i['danbooru_id'] for _, i in results if 'danbooru_id' in i][0]

                    danbooru_result = Booru().get_from_id(danbooru_id)
                else:
                    print(NOT_FOUND)
            elif danbooru_result:
                print(OKAY)
                danbooru_result = danbooru_result[0]
            else:
                print(NOT_FOUND)

            if danbooru_result:
                b_image = BImage(danbooru_result)

                if (b_image.char_count >= 1 and self.sort_by != self.SERIES) or \
                        (b_image.copy_right_count >= 1 and self.sort_by != self.CHARACTER):
                    self.copy_move_file(file_, filename_long, b_image)
                else:
                    self.mark_unknown(file_)
                    print(ERROR_PROMPT + 'File was identified but no relevant information was found.')
            else:
                self.mark_unknown(file_)
                print(ERROR_PROMPT + 'File could not be identified.')

        if skipped:
            print(f'{ERROR_PROMPT}Skipped {skipped} images previously marked as unknown.')
        print(f'{MAJOR_PROMPT}All Operations finished\n')

    def mark_unknown(self, path: str) -> None:
        self.unknown.append(path)
        with open('unknown.txt', 'w') as file_:
            file_.write('\n'.join(self.unknown))

    @staticmethod
    def ask(prompt, options=None, preamble=None):
        print(PREAMBLE_PROMPT + prompt)
        if preamble:
            for line in preamble.split('\n'):
                print(PREAMBLE_SUB + line)
        if options:
            option_line = '   '.join(f'[{i[0].upper()}]{i[1:]}' for i in options)
            option_line += '   [Q]uit'
            print(f'{PREAMBLE_PROMPT}{option_line}')

        value = input(INPUT_PROMPT).strip()
        print()

        if options:
            return {i[0].upper(): i for i in options}.get((value or ' ')[0].upper())
        return value

    def get_settings(self) -> bool:
        if self.base_directory is None:
            directory = self.ask('Enter image directory:')

            self.base_directory = directory or os.getcwd()
            if not os.path.exists(directory):
                print(f'{ERROR_PROMPT}{directory} is not a valid directory.')
                return False
        print(f'{BOLD}Directory "{self.base_directory}" selected.\n')

        if self.sort_by is None:
            self.sort_by = self.ask('Sort by', [self.SERIES, self.CHARACTER, self.BOTH])
            if self.sort_by is None:
                return False
        if self.file_operation is None:
            self.file_operation = self.ask('File processing manner:', [self.MOVE, self.COPY])
            if self.file_operation is None:
                return False
        if self.md5_option is None:
            self.md5_option = self.ask('Hash calculation:', [self.HARD, self.SOFT],
                                       'Hard always uses file-hashes.\n'
                                       ' Lower success rate and speed but no false positives.\n'
                                       'Soft first looks for hashes in filenames.\n'
                                       ' Faster and better success rate, but may have false positives.')
            if self.md5_option is None:
                return False
        if self.multiple_operation is None:
            self.multiple_operation = self.ask('Multiple tags/characters/series in the same image:',
                                                [self.COPIES, self.MIXED, self.FIRST, self.SKIP])
            if self.multiple_operation is None:
                return False
        if self.do_reverse_image is None:
            self.do_reverse_image = self.ask('Reverse image search images not found through hashing:', ['Yes', 'No'])
            if self.do_reverse_image is None:
                return False
            self.do_reverse_image = self.do_reverse_image == 'Yes'
        if self.do_reverse_image and self.image_host is None:
            self.image_host = self.ask('Image host:', [self.IMGUR, self.NOLIFE])
            if self.image_host is None:
                return False

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
        sort_by = self.sort_by
        if sort_by == self.BOTH:
            sort_by = self.CHARACTER

            tds = b_image.copy_rights if self.multiple_operation == self.COPIES else \
                  [b_image.copy_rights_string] if self.multiple_operation == self.MIXED else \
                  [b_image.copy_rights[0]] if self.multiple_operation == self.FIRST else []
        else:
            tds = ['']

        if self.multiple_operation == self.COPIES and self.file_operation == self.COPY:
            store_dir = os.path.join(self.base_directory, '.images')
            print(ACTION_PROMPT + f'Moving to {store_dir}')
            if not os.path.exists(store_dir):
                os.makedirs(store_dir)
            os.rename(file_, os.path.join(store_dir, filename))
            file_ = os.path.join(store_dir, filename)

        for base_directory in tds:
            base_directory = os.path.join(self.base_directory, base_directory)
            if not os.path.exists(base_directory):
                os.makedirs(base_directory)

            if sort_by == self.CHARACTER:
                target_folders = b_image.characters if self.multiple_operation == self.COPIES else \
                                 [b_image.characters_string] if self.multiple_operation == self.MIXED else \
                                 [b_image.characters[0]] if self.multiple_operation == self.FIRST else []
            else:
                target_folders = b_image.copy_rights if self.multiple_operation == self.COPIES else \
                                 [b_image.copy_rights_string] if self.multiple_operation == self.MIXED else \
                                 [b_image.copy_rights[0]] if self.multiple_operation == self.FIRST else []

            # Copy/move file in target folder(s)
            for n, src_target_folder in enumerate(target_folders):
                target_file = os.path.join(base_directory, src_target_folder, filename)
                target_folder = os.path.dirname(target_file)

                if not os.path.exists(target_folder):
                    os.makedirs(target_folder)

                if self.file_operation == self.COPY:
                    if self.multiple_operation == self.COPIES:
                        print(ACTION_PROMPT + f'Linking to {target_folder}')
                        cwd = os.getcwd()
                        os.chdir(target_folder)
                        f = os.path.join('..', '..' if self.sort_by == self.BOTH else '', '.images', filename)
                        os.symlink(f, filename)
                        os.chdir(cwd)
                    else:
                        print(ACTION_PROMPT + f'Copying to {target_folder}')
                        copyfile(file_, target_file)
                elif self.file_operation == self.MOVE:
                    print(ACTION_PROMPT + f'Moving to {target_folder}')
                    if n == len(target_folders) - 1:
                        if os.path.exists(target_file):
                            os.remove(target_file)
                        os.rename(file_, target_file)
                    else:
                        copyfile(file_, target_file)


if __name__ == '__main__':
    Program()
