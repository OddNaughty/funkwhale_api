import colorama
import sys
import requests

colorama.init(autoreset=True)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def error_log(s):
    eprint(colorama.Fore.RED + s)

def crawl_endpoint(start_url, prefix=""):
    next_page = start_url
    while True:
        print(f"Getting page: {next_page}")
        try:
            req = requests.get(next_page)
        except requests.exceptions.SSLError:
            error_log("[SSL ERROR] Url: {}".format(next_page))
            break
        except ConnectionRefusedError:
            error_log("[Connection Refused] Url: {}".format(next_page))
            break
        if req.status_code != 200:
            handle_error_request(req, prefix)
            break
        res = req.json()
        yield res["results"]
        next_page = res["next"]
        if not next_page:
            break


def handle_error_request(req, prefix):
    if req.status_code == 401:
        error_log(f"{prefix}: No authorization for getting {req.url}")