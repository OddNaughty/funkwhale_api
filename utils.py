import colorama
import sys

colorama.init(autoreset=True)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def error_log(s):
    eprint(colorama.Fore.RED + s)