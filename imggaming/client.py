import requests
import json
import time
import os

class VOD:
        
        def __init__(self, vod_data):
            self.id = vod_data['id']
            self.title = vod_data['title']
            self.max_height = vod_data['maxHeight']
            self.stream_links = vod_data['stream_links']
            self.type = vod_data['type']
            
        def __str__(self):
            return f'VOD: {self.title} ({self.id})'
        
        def __repr__(self):
            return f'VOD: {self.title} ({self.id})'
        
        def get_stream_link(self, height=None):
            if not height:
                height = self.max_height
            try:
                return self.stream_links[height]
            except:
                return None

class API:
    
    def __init__(self, verbose: bool = False):
        self.AuthToken = None
        self.RefreshToken = None
        self.verbose = verbose
    
    def _compile_headers(self, auth):
        X_API_KEY = '857a1e5d-e35e-4fdf-805b-a87b6f8364bf'
        headers = {'Content-Type': 'application/json;', 'Referer': 'https://ufcfightpass.com/', 'Origin': 'https://ufcfightpass.com', 'Realm': 'dce.ufc', "Host": 'dce-frontoffice.imggaming.com', 'app': 'dice', 'x-app-var': '6.0.1.98b90eb'}
        headers['x-api-key'] = X_API_KEY
        if auth:
            headers['Authorization'] = f'Bearer {self.AuthToken}'
        return headers
    
    """
    Returns a string containing the authorization headers for the imggaming api. The string is formatted as a series of key-value pairs, with each pair separated by a newline character
    The string can be used directly in the ffmpeg command as the header string. 
    """
    def compile_headers_ffmpeg(self): #To be used for ffmpeg headers
        headers = self._compile_headers(True)
        if not headers:
            print('[ERROR] Could not compile headers for ffmpeg')
            return None
        headers_string = ''
        for key in headers:
            value = headers[key]
            headers_string += f'{key}: {value}\n'
        return headers_string
        
    """Takes an id and returns a boolean indicating whether the item is playable (i.e. a VOD)"""
    def _is_playable(self, vod: dict):
        try:
            return vod['type'] in ['VOD_VIDEO', 'VOD']
        except:
            return None
    
    """Given an id, returns whether the item is a VOD or a playlist, by querying the api endpoints for each type."""
    def vod_or_playlist(self, id):
        vod_data = self.get_vod_data(id)
        if vod_data:
            return 'VOD'
        
        list_ids = self.unpack_playlist(id)
        if list_ids:
            return 'PLAYLIST'
        return None
            
    
    """
    Gets the playback data for a given vod (id), including the title, max height, and stream links, from the imggaming api. (Gets urls from get_vod_data, then gets stream links from those urls)
    args:   vod_id: int, the id of the vod to get playback data for
    returns: dict, containing the title, max_height, and stream_links(dict), refer to the documentation for more information.
    """
    def get_playback_data(self, vod_id: int) -> dict:
        vod_data = self.get_vod_data(vod_id)
        
        if not vod_data:
            print(f'[ERROR] Could not get vod data for vod_id: {str(vod_id)}') if self.verbose else None
            return None   
        
        if not self._is_playable(vod_data):
            print(f'[ERROR] VOD is not playable: {str(vod_id)}') if self.verbose else None
            return None
        
        title = vod_data['title']
        callback_url = vod_data['playerUrlCallback']
        max_height = vod_data['maxHeight']
        
        headers = self._compile_headers(auth=True)
        response = requests.get(callback_url, headers=headers)
        
        if response.status_code in [200, 201]:
            pass
        elif response.status_code == 401:
            if self.authenticate():
                return self.get_playback_data(vod_id)
        else:
            print('[ERROR] Could not get playback data. HTTP status code: ' + str(response.status_code))
            return None
        
        return {'title': title, 'max_height': max_height, 'stream_links': response.json()}
    
    """
    Performs a search query against the imggaming api, for vods and playlists.
    Returns a json object containing the search results
    args:   search_term: str, the term to search for
            filter: str, optional, the type of vod to search for (e.g. 'VOD_VIDEO', 'VOD_PLAYLIST')
            hits: int, optional, the number of results to return
    returns: json(dict), containing the search results
    """
    def search(self, search_term, **kwargs):
        if len(kwargs.keys()) > 2:
            print('[ERROR] Too many search arguments, string \"filter\" and int \"hits\" are the only valid arguments.')
            return False        
        filter = kwargs.get('filter', None)
        hits = kwargs.get('hits', 100)
        
        ALGOLIA_API_KEY = 'e55ccb3db0399eabe2bfc37a0314c346'
        ALGOLIA_APP_ID = 'H99XLDR8MJ'
        search_url = f'https://h99xldr8mj-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia for JavaScript (3.35.1); Browser&x-algolia-application-id={ALGOLIA_APP_ID}&x-algolia-api-key={ALGOLIA_API_KEY}'
        
        options = f'&hitsPerPage={hits}'
        if filter:
            options += f'&facetFilters=%5B%22type%3A{filter}%22%5D'
        body = f'{{"requests":[{{"indexName":"prod-dce.ufc-livestreaming-events","params":"query={search_term}{options}"}}]}}'
        
        headers = self._compile_headers(auth=True)
        headers['Host'] = 'h99xldr8mj-dsn.algolia.net'  #Override search-specific headers
        headers['content-type'] = 'application/x-www-form-urlencoded'
        
        response = requests.post(search_url, headers=headers, data=body)
        
        if response.status_code in [200, 201]:
            pass
        elif response.status_code == 401:
            if self.authenticate():
                return self.search(search_term, **kwargs)
        else:
            print('[ERROR] Could not search for vods. HTTP status code: ' + str(response.status_code))
            return None
        
        return response.json()
    
    """
    Preforms a browse query against the imggaming cdn, for vods and playlists.
    Returns a json object containing the browse results
    args:   buckets: int, the number of buckets to return, defaults to 10
            rows: int, the number of rows to return, defaults to 12
    returns: json(dict), containing the browse results
    """
    def browse(self, buckets=10, rows=12) -> dict:
        bspp = 20 #No idea what this is, possibly bucket shortcut per page?
        browse_url = f'''https://dce-frontoffice.imggaming.com/api/v4/content/browse?bpp={buckets}&rpp={rows}&displaySectionLinkBuckets=SHOW&displayEpgBuckets=HIDE&displayEmptyBucketShortcuts=SHOW&displayContentAvailableOnSignIn=SHOW&displayGeoblocked=HIDE&bspp={bspp}'''
                
        headers = self._compile_headers(auth=True)
        response = requests.get(browse_url, headers=headers)
        
        if response.status_code in [200, 201]:
            pass
        elif response.status_code == 401:
            if self.authenticate():
                return self.browse(buckets=buckets, rows=rows)
        else:
            print('[ERROR] Could not browse for vods. HTTP status code: ' + str(response.status_code))
            return None        
        return response.json()
        
        
    """
    Takes in a vod id and returns the json results for that vod from the api endpoint. Int vod ids auto-convert to str.
    https://dce-frontoffice.imggaming.com/api/v4/vod/41346?includePlaybackDetails=URL
    args:   vod: int, the id of the vod to get data for
    returns: json(dict), containing the vod data
    """
    def get_vod_data(self, vod: int|str) -> dict:
        if type(vod) == int:
            vod = str(vod)
        vod_url = f'https://dce-frontoffice.imggaming.com/api/v4/vod/{vod}?includePlaybackDetails=URL'
        headers = self._compile_headers(auth=True)
        response = requests.get(vod_url, headers=headers)
        
        if response.status_code in [200, 201]:
            pass
        elif response.status_code == 401:
            if self.authenticate():
                return self.get_vod_data(vod)
        else:
            print('[ERROR] Could not get vod data. HTTP status code: ' + str(response.status_code)) if self.verbose else None
            return None

        return response.json()
    
    """Takes in a playlist id and returns the json results for that playlist from the api endpoint. Int playlist ids auto-convert to str."""
    def get_playlist_data(self, playlist: int|str) -> dict:
        if type(playlist) == int:
            playlist = str(playlist)
        playlist_url = f'https://dce-frontoffice.imggaming.com/api/v4/playlist/{playlist}?bpp=undefined&rpp=250&displaySectionLinkBuckets=HIDE&displayEpgBuckets=HIDE&displayEmptyBucketShortcuts=SHOW'
        headers = self._compile_headers(auth=True)
        response = requests.get(playlist_url, headers=headers)
        
        if response.status_code in [200, 201]:
            pass
        elif response.status_code == 401:
            if self.authenticate():
                return self.get_playlist_data(playlist)
        else:
            print('[ERROR] Could not get playlist data. HTTP status code: ' + str(response.status_code))
            return None
        
        return response.json()
    
    """
    Takes a playlist id as input and returns a list of vod ids contained in the playlist. Returns None if the playlist is empty or does not exist. 
    Can return up to 250 vods from a playlist. (NOTE: This may be able to be increased by changing the bpp parameter in the url, but this is untested.)
    args:   playlist: int, the id of the playlist to unpack
    returns: id_list: list[int], a list of vod ids
    """
    def unpack_playlist(self, playlist: int|str) -> list[int]:
        if type(playlist) == int:
            playlist = str(playlist)
        playlist_url = f'https://dce-frontoffice.imggaming.com/api/v4/playlist/{playlist}?bpp=undefined&rpp=250&displaySectionLinkBuckets=HIDE&displayEpgBuckets=HIDE&displayEmptyBucketShortcuts=SHOW'
        headers = self._compile_headers(auth=True)
        response = requests.get(playlist_url, headers=headers)
        
        if response.status_code in [200, 201]:
            pass
        elif response.status_code == 401:
            if self.authenticate():
                return self.unpack_playlist(playlist)
        else:
            print('[ERROR] Could not unpack playlist. HTTP status code: ' + str(response.status_code))
            return None
        
        playlist = response.json()
        vods = playlist['vods']
        id_list = []
        for vod in vods:
            if vod['type'] == 'VOD':
                id_list.append(int(vod['id']))
        return id_list
    
        
    
    """Returns a boolean indicating whether authentication was successful"""
    def authenticate(self, id:str = None, secret:str = None):
        login_url = 'https://dce-frontoffice.imggaming.com/api/v2/login'
        headers = self._compile_headers(auth=False)
        
        if not id or not secret:
            try:
                id = os.environ['IMGGAMING_AUTH_ID']
                secret = os.environ['IMGGAMING_AUTH_PASS']
            except:
                print('[ERROR] No credentials provided, neither parameters nor environment variables.')
                return None
        
        credentials = {'id': id, 'secret': secret}

        try:
            response = requests.post(login_url, headers=headers, json=credentials)
        except requests.exceptions.RequestException as e:
            print('[ERROR] Could not connect to server (Authentication)')
            return None
        
        if response.status_code in [200, 201]:
            pass
        else:
            print('[ERROR] Could not authenticate. HTTP status code: ' + str(response.status_code))
            return None

        res_json = response.json()
        self.AuthToken = res_json['authorisationToken']
        self.RefreshToken = res_json['refreshToken']
        
        return True


def test_main():
    import pprint
    client = API()
    client.authenticate()
    franklin_vs_le = 30852
    print(client.vod_or_playlist(franklin_vs_le))
    print(client.vod_or_playlist(9330))
    
if __name__ == '__main__':
    test_main()