from tinydb import TinyDB

from .fw_albums import FWAlbums, FWAlbum
from .fw_instances import FWInstances, FWInstance

db = TinyDB("fw_db.json")