import os
import json
import requests
import utils

from tinydb import where

class FWInstances(object):
    _instances_list_url = "https://network.funkwhale.audio/dashboards/api/tsdb/query"
    _headers = {
            'Content-Type': 'application/json;charset=utf-8',
        }

    def __init__(self, db, create_if_empty=True):
        self.db_root = db
        self.db = db.table("instances")
        # print("kaka")
        # print(self.db)
        if self.db.all() == []:
            if create_if_empty:
                self.instances_urls = self.get_urls_http()
                self.instances = [FWInstance(self.db_root, url=url) for url in self.instances_urls]
                self.save_db()
            else:
                self.instances_urls = None
                self.instances_urls = None
        else:
            self.instances_urls = self.get_urls_db()
            self.instances = self.get_instances()
            

    def get_urls_http(self):
        # * Si on connait un peu grafana, y'a grave moyen que la requete ne dure pas aussi longtemps, en modifiant la vieille requete SQL
        try:
            instances = requests.post(self._instances_list_url, headers=self._headers, data="""
                {"from":"1581188085935","to":"1588960485935","queries":[{"refId":"A","intervalMs":7200000,"maxDataPoints":1280,"datasourceId":1,"rawSql":"SELECT * FROM (\\n  SELECT\\n    DISTINCT on (c.domain) c.domain as \\"Name\\",\\n    c.up as \\"Is up\\",\\n    coalesce(c.open_registrations, false) as \\"Open registrations\\",\\n    coalesce(anonymous_can_listen, false) as \\"Anonymous can listen\\",\\n    coalesce(c.usage_users_total, 0) as \\"Total users\\",\\n    coalesce(c.usage_users_active_month, 0) as \\"Active users (this month)\\",\\n    coalesce(c.software_version_major, 0)::text || \'.\' || coalesce(c.software_version_minor, 0)::text || \'.\' || coalesce(c.software_version_patch, 0)::text as \\"Version\\",\\n    c.time as \\"Last checked\\",\\n    d.first_seen as \\"First seen\\"\\n  FROM checks as c\\n  INNER JOIN domains AS d ON d.name = c.domain\\n  WHERE d.blocked = false AND c.up = true AND c.time > now() - INTERVAL \'7 days\'\\n  ORDER BY c.domain, c.time DESC\\n) as t ORDER BY \\"Active users (this month)\\"  DESC","format":"table"}]}
                """).json()['results']['A']['tables'][0]['rows']
            instances_urls = [f"https://{instance[0]}" for instance in instances]
            return instances_urls
        except requests.RequestException as e:
            print(e)
        return None

    def save_db(self, cascade=True):
        if cascade:
            for instance in self.instances:
                instance.save_db()
        self.db.insert({"type": "params", "urls": self.instances_urls})

    def get_urls_db(self):
        return self.db.get(where("type") == "params").get("instances_urls")

    def get_instances(self):
        return [FWInstance(self.db_root, instance=instance) for instance in self.db.search(where("type") == "instance")]
    
    def erase_db(self):
        self.db.truncate()

class FWInstance(object):

    def __init__(self, db, **kwargs):
        creation = {"instance": self.create_instance, "url": self.create_url}
        for key, arg in kwargs.items():
            if creation[key]:
                creation[key](arg)
                break
        self._db_root = db
        self._db = db.table("instances")

    def __repr__(self):
        to_repr = {"url": self._url, "albums": self._albums}
        return f"{to_repr}"
    
    def create_instance(self, params):
        self._url = params["url"]
        self._albums = params["albums"]
    
    def create_url(self, url):
        self._url = url
        self._albums = None

    def save_db(self):
        return self._db.insert({
            "type": "instance",
            "url": self._url,
            "albums": self._albums
        })