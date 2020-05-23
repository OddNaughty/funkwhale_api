import os
import json
import requests
import utils

class FWInstances(object):
    _instances_list_url = "https://network.funkwhale.audio/dashboards/api/tsdb/query"
    _headers = {
            'Content-Type': 'application/json;charset=utf-8',
        }

    def __init__(self, create=True):
        os.makedirs("exports", exist_ok=True)
        try:
            f = open("exports/instances_urls.json", "r")
            self.instances_urls = json.load(f)["instances_urls"]
        except FileNotFoundError:
            if create:
                self.instances_urls = self.http_get_all()
                self.export_file()
            else:
                self.instances_urls = None

    def http_get_all(self):
        # * Si on connait un peu grafana, y'a grave moyen que la requete ne dure pas aussi longtemps, en modifiant la vieille requete SQL
        try:
            instances = requests.post(self._instances_list_url, headers=self._headers, data="""
                {"from":"1581188085935","to":"1588960485935","queries":[{"refId":"A","intervalMs":7200000,"maxDataPoints":1280,"datasourceId":1,"rawSql":"SELECT * FROM (\\n  SELECT\\n    DISTINCT on (c.domain) c.domain as \\"Name\\",\\n    c.up as \\"Is up\\",\\n    coalesce(c.open_registrations, false) as \\"Open registrations\\",\\n    coalesce(anonymous_can_listen, false) as \\"Anonymous can listen\\",\\n    coalesce(c.usage_users_total, 0) as \\"Total users\\",\\n    coalesce(c.usage_users_active_month, 0) as \\"Active users (this month)\\",\\n    coalesce(c.software_version_major, 0)::text || \'.\' || coalesce(c.software_version_minor, 0)::text || \'.\' || coalesce(c.software_version_patch, 0)::text as \\"Version\\",\\n    c.time as \\"Last checked\\",\\n    d.first_seen as \\"First seen\\"\\n  FROM checks as c\\n  INNER JOIN domains AS d ON d.name = c.domain\\n  WHERE d.blocked = false AND c.up = true AND c.time > now() - INTERVAL \'7 days\'\\n  ORDER BY c.domain, c.time DESC\\n) as t ORDER BY \\"Active users (this month)\\"  DESC","format":"table"}]}
                """).json()['results']['A']['tables'][0]['rows']
            instances_urls = [f"https://{instance[0]}" for instance in instances]
            print(instances_urls)
            return instances_urls
        except requests.RequestException as e:
            print(e)
        return None

    def export_file(self):
        with open("exports/instances_urls.json", "w") as f:
            json.dump({"instances_urls": self.instances_urls}, f)


class FWInstance(object):

    def __init__(self):
        pass