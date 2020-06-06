from FW.app import db_root

def get_all_instances_url():
    set([i["url"] for i in db_root.table("instance").all()])