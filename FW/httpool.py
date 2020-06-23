import asyncio
import signal
import requests
import logging
import random

import aiohttp

from asyncio import Task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


class RateLimitReached(Exception):
    pass

class Gathered(object):

    def __init__(self, urls):
        self.pending_urls = [urls]
        self.finished_urls = []

async def clean_pending_tasks(caller):
    logging.info("CLEANING TASKS")
    current_task = asyncio.current_task()
    tasks = []
    for t in asyncio.all_tasks():
         if t is not current_task and t is not caller:
            # logging.debug("Adding task to cleansing: {}".format(t))
            tasks.append(t)
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)

async def shutdown(loop, s=None):
    if s:
        logging.info(f"Received exit signal {s.name}...")
    logging.info("I'm shutting down you bitch")
    await asyncio.gather(clean_pending_tasks(asyncio.current_task()))
    loop.stop()
    logging.info("I'm really down")

def handle_rate_limit_exception(loop, context):
    exception = context.get("exception", None)
    if exception and type(exception) == RateLimitReached:
        logging.error("RATE LIMIT REACHED")
        # asyncio.create_task(switch_to_rate_limitation(loop))
    elif exception:
        logging.error("OH MY GOD THIS IS ANOTHER EXCEPTION")
        asyncio.create_task(shutdown(loop))
        raise exception
    else:
        logging.info("Creating shutdown task")
        asyncio.create_task(shutdown(loop))

async def fetch_real_url(session, url, page=1):
    # if page == 2:
        # await asyncio.sleep(1)
        # raise RateLimitReached
    async with session.get(url, params={"page": page}, raise_for_status=True) as req:
        logging.info("Getting url: {}".format(req.url))
        res = await req.json()
        # logging.info("headers: {}".format(req.headers))
        if req.headers["x-ratelimit-remaining"] == 0:
            raise RateLimitReached 
        albums_ids = [a["id"] for a in res["results"]]
        return (url, page, albums_ids)

async def fetch_until_ratelimit(session):
    url_to_fetch = {
        ("https://open.audio/api/v1/albums", n): None for n in range(1, 6)
    }
    tasks = [asyncio.create_task(fetch_real_url(session, "https://open.audio/api/v1/albums", n)) for n in range(1, 6)]
    for r in asyncio.as_completed(set(tasks)):
        try:
            (url, page, ids) = await r
            url_to_fetch[url, page] = ids
        except RateLimitReached:
            logging.error("RATE LIMIT REACHED MUAHAHA")
            return (False, url_to_fetch)
        except Exception as e:
            logging.error(e)
            raise e
    return (True, url_to_fetch)

    # done, pending = await asyncio.wait(set([fetch_real_url(session, "https://open.audio/api/v1/albums", params={"page": n}) for n in range(1, 6)]), return_when=asyncio.FIRST_EXCEPTION)
    # logging.debug(done)
    # logging.debug(pending)
    # return (done, pending)
    # albums_ids = []
    # for r in asyncio.as_completed(set([fetch_real_url(session, "https://open.audio/api/v1/albums", params={"page": n}) for n in range(1, 6)])):
    #     try:
    #         res = await r
    #     except RateLimitReached:
    #         logging.error("RATE LIMIT REACHED MUAHAHA")
    #         return (False, albums_ids)
    #     albums_ids.extend(res)
    # return (True, albums_ids)


async def launch_album_crawl():
    albums_ids = []
    async with aiohttp.ClientSession() as session:
        success, url_to_fetch = await fetch_until_ratelimit(session)
        if success:
            logging.info("SUCCEEEESSS WITHOUT RATELIMITED")
            return 
        else:
            logging.error("YES, WE HAVE BEEN RATELIMITED")
            await clean_pending_tasks(asyncio.current_task())
            await shutdown(asyncio.get_event_loop())
    logging.info("Albums_ids: {}".format(albums_ids))

async def recursive_one(iteration):
    logging.info("Waiting iteration {}".format(iteration))
    await asyncio.sleep(0.01)
    return await asyncio.gather(recursive_one(iteration+1))

def main():
    # TODO: Use asyncio.wait(FIRST_EXCEPTION ?)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(loop, s))
        )
    loop.set_exception_handler(handle_rate_limit_exception)
    try:
        loop.run_until_complete(launch_album_crawl())
        # loop.create_task(recursive_one(0))
        # loop.run_forever()
    except asyncio.CancelledError:
        logging.error("It's very bad this task was cancelled...")
    finally:
        loop.close()
        logging.info("THIS IS OVER")


