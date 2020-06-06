import json
import requests
import pprint

pp = pprint.PrettyPrinter()

OPEN_AUDIO_URL = 'https://open.audio'
GAFAM_URL = 'https://audio.gafamfree.party'


class Album:
    _URL = '/api/v1/albums'

    __slots__ = ('ids', 'library_ids', 'all_albums')
    def __init__(self, all_albums=False):
        self.all_albums = all_albums
        self.ids = []
        self.library_ids = []
        self._get_playable_album_ids()
        self._get_library_uuids()
    
    def _get_album_count(self):
        response = requests.get("".join([OPEN_AUDIO_URL, Album._URL, '/?playable=true']))
        if response.status_code == 200:
            return response.json().get('count', 1)
        return 1

    def _get_playable_album_ids(self):
        count = 1 if not self.all_albums else self._get_album_count()

        for nb in range(0, count):
            page_url = f'/?page{nb}&playable=true'
            response = requests.get("".join([OPEN_AUDIO_URL, Album._URL, page_url]))
            if response.status_code == 200:
                ids = [album['id']
                        for album in response.json().get('results', [])]
                self.ids.extend(ids)

    def _get_library_uuids(self):
        for album_id in self.ids:
            libs_url = f'/{album_id}/libraries'
            response = requests.get("".join([OPEN_AUDIO_URL, Album._URL, libs_url]))
            if response.status_code == 200:
                uuids = [lib['uuid']
                        for lib in response.json().get('results', [])]
                self.library_ids.extend(uuids)
            

class MyFunkwhaleInstance:
    def __init__(self, login, password):
        self.token = {'jwt': ''}
        self.credentials = {'username': login, 'password': password}

        self.connect()
        print(self.token)
        self._get_myself()

    def connect(self):
        response = requests.post("".join([GAFAM_URL, '/api/v1/token']), json=self.credentials)
        if response.status_code == 200:
            self.token = response.json()


    def _get_myself(self):
        response = requests.get("".join([GAFAM_URL, '/api/v1/libraries']), params=self.token)
        print(response)
        if response.status_code == 200:
            print(response.json())

## https://docs.funkwhale.audio/federation/index.html?highlight=rest%20route#supported-activities
if __name__ == '__main__':
    albums = Album()
    print(albums.ids)
    print(albums.library_ids)

