import operator
import functools
import requests

from tinydb import where


import FW.utils

from FW.app import db_root
from FW.models.exceptions import FWDBUpdateErrorNoId

db = db_root.table("album")

class FWAlbumFactory(object):

    def __init__(self, url):
        if isinstance(url, str):
            self.instance_url = url
        else:
            self.instance_url = url.url
        self.url = f"{self.instance_url}/api/v1/albums"

    def __repr__(self):
        return f"<FWAlbumFactory:'{self.instance_url}'>"

    def next_albums(self):
        for album in FW.utils.crawl_endpoint(self.url, "Album"):
            yield album

    def discover_albums(self):
        albums = functools.reduce(operator.iconcat, [albums for albums in self.next_albums()], [])
        return albums

    def generate_album(self, album):
        return FWAlbum({
            "instance_url": self.instance_url,
            "fw_id": album["id"],
        })

    def get_album(self, cond=None, uid=None):
        res = None
        if uid:
            res = db.get(doc_id=uid)
        else:
            res = db.get(cond)
        if not res:
            return None
        res["_uid"] = res.doc_id
        return FWAlbum(res)

    def all(self):
        return [FWAlbum(params) for params in db.search(where("type") == "album")]


    def populate_db(self):
        albums_res = self.discover_albums()
        albums = [self.generate_album(album) for album in albums_res]
        uids = db.insert_multiple([a.__db_repr__() for a in albums])
        for (uid, album) in zip(uids, albums):
            album._id = uid
        return albums


class FWAlbum(object):

    def __init__(self, params):
        self.db = db_root.table("album")
        self.instance_url = params["instance_url"]
        self.fw_id = params["fw_id"]
        self._uid = getattr(params, "doc_id", None)
        self.url = f"{self.instance_url}/api/v1/albums/{self.fw_id}"
        self.libraries_url = f"{self.url}/libraries"
        self.libraries = params.get("libraries")

    def __repr__(self):
        return f"<FWAlbum:'{self.url}'>"

    def __db_repr__(self):
        return {
            "instance_url": self.instance_url,
            "fw_id": self.fw_id,
            "libraries": self.libraries,
            "type": "album"
        }

    def save(self):
        if self._uid != None:
            self.db.update(self.__db_repr__(), doc_ids=[self._uid])
        else: 
            self._uid = self.db.insert(self.__db_repr__())
        return self._uid

    def set_libraries_ids(self):
        libraries = functools.reduce(operator.iconcat, FW.utils.crawl_endpoint(self.libraries_url, "Album Libraries"))
        libraries_ids = [library["uuid"] for library in libraries]
        self.libraries = libraries_ids
        return libraries_ids

def get(query):
    return FWAlbum(db.get(query))

def reset():
    db.truncate()

def set_libraries(doc):  
    libraries_url = f"{doc['instance_url']}/api/v1/albums/{doc['fw_id']}/libraries"
    libraries = functools.reduce(operator.iconcat, FW.utils.crawl_endpoint(libraries_url, "Album Libraries"))
    libraries_ids = [library["uuid"] for library in libraries]
    doc["libraries"] = libraries_ids

def update_libraries():
    db.update(set_libraries, ~ (where("libraries").exists()))
