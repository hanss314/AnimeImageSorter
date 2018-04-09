import sys
import os


PREAMBLE_PROMPT = '==> '
ACTION_PROMPT = ':: '
PREAMBLE_SUB = ':: '
INPUT_PROMPT = '-> '
MAJOR_PROMPT = '==> '
MINOR_PROMPT = '  -> '
ERROR_PROMPT = ':: '
NORMAL = ''
BOLD = ''

NOT_FOUND = '[Not found]'
OKAY = '[Okay]'


if sys.stdout.isatty() and os.name != 'nt':
    # We can use colour
    PREAMBLE_PROMPT = '\033[1;33m==> \033[1;37m'
    ACTION_PROMPT = '\033[1;35m:: \033[0;37m'
    PREAMBLE_SUB = '\033[1;33m:: \033[0;37m'
    INPUT_PROMPT = '\033[1;33m-> \033[0;37m'
    MAJOR_PROMPT = '\033[1;32m==> \033[1;37m'
    MINOR_PROMPT = '\033[1;34m  -> \033[0;37m'
    ERROR_PROMPT = '\033[1;32m:: \033[0;37m'
    NORMAL = '\033[0;37m'
    BOLD = '\033[1;37m'

    NOT_FOUND = '\033[0;31m[Not found]'
    OKAY = '\033[0;34m[Okay]'
