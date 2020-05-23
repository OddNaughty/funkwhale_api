#!/usr/bin/env python3

import datetime
import json
import os
import re
import urllib.parse
import operator
from functools import reduce

from requests import get, post

albums_endpoint = "{instance_url}/api/v1/albums?playable=true"
albums_libraries_endpoint = "{instance_url}/api/v1/albums/{album_id}/libraries"
instances_list_url = "https://network.funkwhale.audio/dashboards/api/tsdb/query"
exports_filename_regex = re.compile(r'albums_(?P<domain>.*).json$')

# TODO: Error management needs to be done and needs to be implemented with try/catch

def get_public_instances():
    # * Si on connait un peu grafana, y'a grave moyen que la requete ne dure pas aussi longtemps, en modifiant la vieille requete SQL
    headers = {
        'Content-Type': 'application/json;charset=utf-8',
    }
    instances = post(instances_list_url, headers=headers, data="""
        {"from":"1581188085935","to":"1588960485935","queries":[{"refId":"A","intervalMs":7200000,"maxDataPoints":1280,"datasourceId":1,"rawSql":"SELECT * FROM (\\n  SELECT\\n    DISTINCT on (c.domain) c.domain as \\"Name\\",\\n    c.up as \\"Is up\\",\\n    coalesce(c.open_registrations, false) as \\"Open registrations\\",\\n    coalesce(anonymous_can_listen, false) as \\"Anonymous can listen\\",\\n    coalesce(c.usage_users_total, 0) as \\"Total users\\",\\n    coalesce(c.usage_users_active_month, 0) as \\"Active users (this month)\\",\\n    coalesce(c.software_version_major, 0)::text || \'.\' || coalesce(c.software_version_minor, 0)::text || \'.\' || coalesce(c.software_version_patch, 0)::text as \\"Version\\",\\n    c.time as \\"Last checked\\",\\n    d.first_seen as \\"First seen\\"\\n  FROM checks as c\\n  INNER JOIN domains AS d ON d.name = c.domain\\n  WHERE d.blocked = false AND c.up = true AND c.time > now() - INTERVAL \'7 days\'\\n  ORDER BY c.domain, c.time DESC\\n) as t ORDER BY \\"Active users (this month)\\"  DESC","format":"table"}]}
        """).json()['results']['A']['tables'][0]['rows']
    return [f"https://{instance[0]}" for instance in instances]


def get_albums_ids(instances_urls, limit=None, save_instance=False):
    instances = {}
    albums_count = 0
    for instance_url in instances_urls:
        albums_ids = set()
        url = albums_endpoint.format(instance_url=instance_url)
        while True:
            print(f"Getting page {url}")
            res = get(f"{url}")
            if res.status_code != 200:
                print(f"HTTP ERROR: {res.status_code}")
                break
            res = res.json()
            new_albums_ids = [album['id'] for album in res['results']]
            albums_ids = albums_ids.union(set(new_albums_ids))
            if limit != None and len(albums_ids) + albums_count>= limit:
                instances[instance_url] = {"ids": list(albums_ids)[:limit-albums_count], "complete": False, "url": instance_url}
                if save_instance:
                    with open(f"exports/{datetime.datetime.now().replace(microsecond=0)}_albums_{urllib.parse.urlparse(instance_url).netloc}.json", 'w') as f:
                        json.dump(instances[instance_url], f)
                return instances
            if not res["next"]:
                break
            url = res["next"]
        instances[instance_url] = {"ids": list(albums_ids), "complete": True, "url": instance_url}
        if save_instance:
            with open(f"exports/{datetime.datetime.now().replace(microsecond=0)}_albums_{urllib.parse.urlparse(instance_url).netloc}.json", 'w') as f:
                json.dump(instances[instance_url], f)
        albums_count += len(albums_ids)
    return instances

# Soon deprecated
def get_albums_ids_from_export_files_v1():
    instances = {}
    try:
        filenames = os.listdir("exports")
        for filename in filenames:
            with open(os.path.join("exports", filename), "r") as file:
                ids = json.load(file)["ids"]
                try:
                    domain = exports_filename_regex.search(filename).group("domain")
                    url = f"https://{domain}"
                    instances[url] = {"ids": ids}
                except AttributeError as e:
                    print("Wrong file in exports: {}".format(e))
    except FileNotFoundError as e:
        print("Exports directory doesn't exist")
    return instances

def get_libraries_id_from_albums_id(instances_albums, limit=None, save_libraries=False):
    # ? J'ai écrit le truc en dessous pour que ce soit plus clair, mais les comprehension lists sont généralement plus rapides
    instances_libraries = {}
    libraries_count = 0
    for (instance_url, albums_ids) in instances_albums.items():
        libraries_uuid = set()
        for album_id in albums_ids["ids"]:
            url = albums_libraries_endpoint.format(instance_url=instance_url, album_id=album_id)
            print(f"Getting page {url}")
            res = get(url)
            if res.status_code != 200:
                print(f"HTTP ERROR: {res.status_code}")
            else:
                uuids = [library["uuid"] for library in res.json()['results']]
                libraries_uuid = libraries_uuid.union(set(uuids))
                if limit != None and len(libraries_uuid) + libraries_count >= limit:
                    instances_libraries[instance_url] = {"ids": list(libraries_uuid)[:limit - libraries_count], "complete": False, "url": instance_url}
                    if save_libraries:
                        with open(f"exports/{datetime.datetime.now().replace(microsecond=0)}_libraries_{urllib.parse.urlparse(instance_url).netloc}.json", "w") as f:
                            json.dump(instances_libraries[instance_url], f)
                    return instances_libraries
        instances_libraries[instance_url] = {"ids": list(libraries_uuid), "complete": True, "url": instance_url}
        libraries_count += len(libraries_uuid)
        if save_libraries:
            with open(f"exports/{datetime.datetime.now().replace(microsecond=0)}_libraries_{urllib.parse.urlparse(instance_url).netloc}.json", "w") as f:
                json.dump(instances_libraries[instance_url], f)
    return instances_libraries

def get_libraries_uuid(album_limit=None, libraries_limit=None, save=True):
    os.makedirs("exports", exist_ok=True)
    instances_urls = get_public_instances()
    instances_albums_id = get_albums_ids(instances_urls, album_limit, save_instance=save)
    instances_libraries_uuid = get_libraries_id_from_albums_id(instances_albums_id, libraries_limit, save_libraries=save)
    # Flatten the list
    libraries_uuid = reduce(operator.iconcat, [i["ids"] for (_, i) in instances_libraries_uuid.items()], [])
    print("Crawled")
    return libraries_uuid

if __name__ == "__main__":
    # TODO: Use a user-friendly display, like dynamic console output using.... CURSES or (https://github.com/peterbrittain/asciimatics)
    print("Script starting")
    get_libraries_uuid()
