import requests

from tinydb import where

from FW.app import db_root
from FW.models.exceptions import FWIdAlreadySet
from FW.models.album import FWAlbumFactory

db = db_root.table("instance")

class FWInstanceFactory():

    _instances_list_url = "https://network.funkwhale.audio/dashboards/api/tsdb/query"

    def __init__(self):
        pass

    def discover_instances(self):
        # * Si on connait un peu grafana, y'a grave moyen que la requete ne dure pas aussi longtemps, en modifiant la vieille requete SQL
        headers = {
            'Content-Type': 'application/json;charset=utf-8',
        }
        instances = requests.post(self._instances_list_url, headers=headers, data="""
            {"from":"1581188085935","to":"1588960485935","queries":[{"refId":"A","intervalMs":7200000,"maxDataPoints":1280,"datasourceId":1,"rawSql":"SELECT * FROM (\\n  SELECT\\n    DISTINCT on (c.domain) c.domain as \\"Name\\",\\n    c.up as \\"Is up\\",\\n    coalesce(c.open_registrations, false) as \\"Open registrations\\",\\n    coalesce(anonymous_can_listen, false) as \\"Anonymous can listen\\",\\n    coalesce(c.usage_users_total, 0) as \\"Total users\\",\\n    coalesce(c.usage_users_active_month, 0) as \\"Active users (this month)\\",\\n    coalesce(c.software_version_major, 0)::text || \'.\' || coalesce(c.software_version_minor, 0)::text || \'.\' || coalesce(c.software_version_patch, 0)::text as \\"Version\\",\\n    c.time as \\"Last checked\\",\\n    d.first_seen as \\"First seen\\"\\n  FROM checks as c\\n  INNER JOIN domains AS d ON d.name = c.domain\\n  WHERE d.blocked = false AND c.up = true AND c.time > now() - INTERVAL \'7 days\'\\n  ORDER BY c.domain, c.time DESC\\n) as t ORDER BY \\"Active users (this month)\\"  DESC","format":"table"}]}
            """).json()['results']['A']['tables'][0]['rows']
        return [f"https://{instance[0]}" for instance in instances]

    def generate_instance(self, url):
        return FWInstance({"url": url})

    def get_instance(self, cond=None, uid=None):
        res = None
        if uid:
            res = db.get(doc_id=uid)
        else:
            res = db.get(cond)
        if not res:
            return None
        res["_uid"] = res.doc_id
        return FWInstance(res)

    def all(self):
        return [FWInstance(params) for params in db.search(where("type") == "instance")]

    def populate_db(self):
        urls = self.discover_instances()
        instances = [self.generate_instance(url) for url in urls]
        uids = db.insert_multiple([i.__db_repr__() for i in instances])
        for (uid, instance) in zip(uids, instances):
            instance.set_id(uid)
        return instances

class FWInstance():
    
    # TODO: Check uniqueness for each url...

    def __init__(self, params):
        self.url = params.get("url")
        self.albums_ids = params.get("albums_ids")
        self.db = db
        self._uid = getattr(params, "doc_id", None)

    def __repr__(self):
        return f"<FWInstance:'{self.url}'>"

    def __db_repr__(self):
        return {
            "url": self.url,
            "albums": self.albums_ids,
            "type": "instance",
        }

    def set_id(self, uid):
        if self._uid:
            raise FWIdAlreadySet()
        self._uid = uid
        return uid

    def save(self):
        if self._uid != None:
            self.db.update(self.__db_repr__(), doc_ids=[self._uid])
        else: 
            self._uid = self.db.insert(self.__db_repr__())
        return self._uid

def reset():
    db.truncate()

def populate_instances():
    factory = FWInstanceFactory()
    return factory.populate_db()

def populate_albums():
    factory = FWInstanceFactory()
    for instance in factory.all():
        f2 = FWAlbumFactory(instance)
        f2.populate_db()
