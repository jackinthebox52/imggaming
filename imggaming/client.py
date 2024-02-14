import requests
import json
import time
import os
# This file will contain the client for the imggaming api
# The client will be used to interact with the imggaming api, and will be used to download UFC fight pass vods

class API:
    
    def __init__(self):
        self.MAINTAINER = 'IMGGAMING'
        
        self.AuthToken = None
        self.RefreshToken = None
        self.OutputDirectory = './output/'
        
    def _compile_headers(self, auth):
        X_API_KEY = '857a1e5d-e35e-4fdf-805b-a87b6f8364bf'
        headers = {'Content-Type': 'application/json;', 'Referer': 'https://ufcfightpass.com/', 'Origin': 'https://ufcfightpass.com', 'Realm': 'dce.ufc', "Host": 'dce-frontoffice.imggaming.com', 'app': 'dice', 'x-app-var': '6.0.1.98b90eb'}
        headers['x-api-key'] = X_API_KEY
        if auth:
            headers['Authorization'] = f'Bearer {self.AuthToken}'
        return headers
    
    def set_ouput_directory(self, directory):
        self.OutputDirectory = directory
        if self.OutputDirectory[-1] != '/':
            self.OutputDirectory += '/'
        print(f'Setting output directory: {self.OutputDirectory}')
        
    def set_mtainainer(self, maintainer):
        if not maintainer.isalnum():
            print('[ERROR] Invalid maintainer')
            return
        self.MAINTAINER = maintainer
    
    def _compile_headers_ffmpeg(self, headers): #To be used for ffmpeg headers
        headers_string = ''
        for key in headers:
            value = headers[key]
            headers_string += f'{key}: {value}\n'
        return headers_string
        
    def _is_playable(self, vod):
        return vod['type'] in ['VOD_VIDEO', 'VOD']
    
    def get_playback_data(self, vod_id):
        vod_data = self.get_vod_data(vod_id)
        
        if not vod_data:
            print('[ERROR] Could not get vod data')
            return None   
        
        if not self._is_playable(vod_data):
            print('[ERROR] VOD is not playable')
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
        
        return {'title': title, 'max_height': max_height, 'playback_data': response.json()}
    
    """
    Preforms a search query against the imggaming cdn, for vods and playlists.
    Returns a json object containing the search results
    args:   search_term: str, the term to search for
            filter: str, optional, the type of vod to search for (e.g. 'VOD_VIDEO', 'VOD_PLAYLIST')
            hits: int, optional, the number of results to return
    """
    def search(self, search_term, **kwargs):
        if len(kwargs.keys()) > 2:
            print('[ERROR] Too many search arguments, string \"filter\" and int \"hits\" are the only valid arguments.')
            return False        
        filter = kwargs.get('filter', None)
        hits = kwargs.get('hits', 100)
        
        ALGOLIA_API_KEY = 'e55ccb3db0399eabe2bfc37a0314c346'
        ALGOLIA_APP_ID = 'H99XLDR8MJ'
        SEARCH_URL = f'https://h99xldr8mj-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia for JavaScript (3.35.1); Browser&x-algolia-application-id={ALGOLIA_APP_ID}&x-algolia-api-key={ALGOLIA_API_KEY}'
        
        options = f'&hitsPerPage={hits}'
        if filter:
            options += f'&facetFilters=%5B%22type%3A{filter}%22%5D'
        body = f'{{"requests":[{{"indexName":"prod-dce.ufc-livestreaming-events","params":"query={search_term}{options}"}}]}}'
        
        headers = self._compile_headers(auth=True)
        headers['Host'] = 'h99xldr8mj-dsn.algolia.net'  #Override search-specific headers
        headers['content-type'] = 'application/x-www-form-urlencoded'
        
        response = requests.post(SEARCH_URL, headers=headers, data=body)
        
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
    """
    def browse(self, buckets=10, rows=12):
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
    Takes in a vod id and returns the json results for that vod from the api endpoint.
    https://dce-frontoffice.imggaming.com/api/v4/vod/41346?includePlaybackDetails=URL
    """
    def get_vod_data(self, vod):
        VOD_URL = f'https://dce-frontoffice.imggaming.com/api/v4/vod/{vod}?includePlaybackDetails=URL'
        headers = self._compile_headers(auth=True)
        response = requests.get(VOD_URL, headers=headers)
        
        if response.status_code in [200, 201]:
            pass
        elif response.status_code == 401:
            if self.authenticate():
                return self.get_vod_data(vod)
        else:
            print('[ERROR] Could not get vod data. HTTP status code: ' + str(response.status_code))
            return None

        return response.json()
    
    """Maximum number of vods to return is 250"""
    def unpack_playlist(self, playlist):
        PLAYLIST_URL = f'https://dce-frontoffice.imggaming.com/api/v4/playlist/{playlist}?bpp=undefined&rpp=250&displaySectionLinkBuckets=HIDE&displayEpgBuckets=HIDE&displayEmptyBucketShortcuts=SHOW'
        headers = self._compile_headers(auth=True)
        response = requests.get(PLAYLIST_URL, headers=headers)
        
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
                id_list.append(vod['id'])
        print(id_list)
        return id_list
    
        
    
    """Returns a boolean indicating whether authentication was successful"""
    def authenticate(self, id=None, secret=None):
        LOGIN_URL = 'https://dce-frontoffice.imggaming.com/api/v2/login'
        headers = self._compile_headers(auth=False)
        if not id or not secret:
            try:
                id = os.environ['IMGGAMING_AUTH_ID']
                secret = os.environ['IMGGAMING_AUTH_PASS']
            except:
                print('[ERROR] No credentials provided, neither paramters nor environment variables.')
                return None
        
        credentials = {'id': id, 'secret': secret}

        try:
            response = requests.post(LOGIN_URL, headers=headers, json=credentials)
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
    client = API()
    client.authenticate()
    franklin_vs_le = 30852
    client.get_vod_data(franklin_vs_le)
    print(client.get_playback_data(franklin_vs_le))
    
if __name__ == '__main__':
    test_main()

