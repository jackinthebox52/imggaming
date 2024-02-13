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
        
        if response.status_code != 200:
            print(response.status_code)
            print('[ERROR] Could not search for vods')
            return False
        
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
        
        if response.status_code != 200:
            print(response.status_code)
            print('[ERROR] Could not browse for vods')
            return False
        
        return response.json()
        
        
    """
    Takes in a vod id and returns the json results for that vod from the api endpoint.
    https://dce-frontoffice.imggaming.com/api/v4/vod/41346?includePlaybackDetails=URL
    """
    def get_vod_data(self, vod):
        VOD_URL = f'https://dce-frontoffice.imggaming.com/api/v4/vod/{vod}?includePlaybackDetails=URL'
        headers = self._compile_headers(auth=True)
        response = requests.get(VOD_URL, headers=headers)
        if response.status_code != 200:
            print(response.status_code)
            print('[ERROR] Could not get vod data')
            return False
        return response.json()
    
    def unpack_playlist(self, playlist):
        PLAYLIST_URL = f'https://dce-frontoffice.imggaming.com/api/v4/playlist/{playlist}?bpp=undefined&rpp=250&displaySectionLinkBuckets=HIDE&displayEpgBuckets=HIDE&displayEmptyBucketShortcuts=SHOW'
        headers = self._compile_headers(auth=True)
        response = requests.get(PLAYLIST_URL, headers=headers)
        
        if response.status_code != 200:
            print(response.status_code)
            print('[ERROR] Could not unpack playlist')
            return False
        
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
                return False
        
        credentials = {'id': id, 'secret': secret}

        try:
            response = requests.post(LOGIN_URL, headers=headers, json=credentials)
        except requests.exceptions.RequestException as e:
            print('[ERROR] Could not connect to server (Authentication)')
            return False
        
        if response.status_code != 201:
            print(response.status_code)
            print('[ERROR] Could not log in (Authentication)')
            return False

        res_json = response.json()
        self.AuthToken = res_json['authorisationToken']
        self.RefreshToken = res_json['refreshToken']
        
        return True
    

def test_main():
    client = API()
    client.authenticate()
    #results = client.search('strickland')
    print(client.browse())
    # for r in results['results'][0]['hits']:
    #    print(r['type'])
    
if __name__ == '__main__':
    test_main()


#This api will be based off of the following code, which is a script that downloads UFC fight pass vods
'''
import requests
import json
import time
from time import strftime, localtime
import os, sys

MAINTAINER = 'GUTHIX'
AUTH_TOKEN = None
REFRESH_TOKEN = None

START_TIME = None
OUTPUT_DIRECTORY = './output/'

def compile_headers(auth):
    X_API_KEY = '857a1e5d-e35e-4fdf-805b-a87b6f8364bf'
    headers = {'Content-Type': 'application/json;', 'Referer': 'https://ufcfightpass.com/', 'Origin': 'https://ufcfightpass.com', 'Realm': 'dce.ufc', "Host": 'dce-frontoffice.imggaming.com', 'app': 'dice', 'x-app-var': '6.0.1.98b90eb'}
    headers['x-api-key'] = X_API_KEY
    if auth:
        headers['Authorization'] = f'Bearer {AUTH_TOKEN}'
    return headers


def compile_headers_string(headers):
    headers_string = ''
    for key in headers:
        value = headers[key]
        headers_string += f'{key}: {value}\n'
    return headers_string


def compile_title_string(event_meta):
    title = event_meta['title']
    title_string = ''
    for w in title.split():
        w = w.replace(':', '')
        title_string += f'{w}.'
    title_string += f'WEBRip-{MAINTAINER}'
    return title_string

def download_all(url, event_meta, suppress_output=True):
    headers = compile_headers(auth=True)
    headers_string = compile_headers_string(headers)

    description = event_meta['description']
    title_string = compile_title_string(event_meta)
    title_directory_path = OUTPUT_DIRECTORY + title_string
    if os.path.exists(title_directory_path):
        print(f'Found files for: {title_string}')
        passed = justify_extant_vod(title_directory_path)
        if not passed:
            print(f'Incomplete files found for: {title_string}')
            return False
        else:
            return True
    os.system(f'mkdir {title_directory_path}')

    ffmpeg_cmd = f'ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -headers "{headers_string}" -i "{url}" -c:v copy {title_directory_path}/{title_string}.incomplete.mkv'
    if suppress_output:
        ffmpeg_cmd += ' > /dev/null 2>&1'
    print(f"Downloading metadata: {title_string}...")
    os.system(f'wget {event_meta["thumbnail_url"]} -O {title_directory_path}/thumbnail.jpg')
    try:
        poster_url = event_meta["poster_url"]
        os.system(f'wget {poster_url} -O {OUTPUT_DIRECTORY}{title_string}/poster.jpg')
    except:
        pass
    print(f"Downloading video: {title_string}...")
    os.system(ffmpeg_cmd) #Run ffmpeg command (blocking)
    os.system(f'mv {title_directory_path}/{title_string}.incomplete.mkv {title_directory_path}/{title_string}.mkv')
    return True

def get_vod_meta(id, hls_url):
    VOD_URL = f'https://dce-frontoffice.imggaming.com/api/v4/vod/{id}?includePlaybackDetails=URL'
    headers = compile_headers(auth=True)
    response = requests.get(VOD_URL, headers=headers) #Get vod data from api
    if response.status_code == 403:
        return False
    if response.status_code != 200:
        login()
        return get_vod_meta(id, hls_url)#Retry request, only if relogin passes

    title = response.json()['title']
    description = response.json()['description']
    thumbnauil_url = response.json()['thumbnailUrl']
    try:
        poster_url = response.json()['posterUrl']
    except:
        poster_url = None
    event_meta = {'vod_id': id, 'title': title, 'description': description, 'thumbnail_url': thumbnauil_url, 'poster_url': poster_url}
    
    return event_meta

def justify_extant_vod(title_directory_path):
    for file in os.listdir(title_directory_path):
        if file.endswith('.mkv'):
            if('incomplete' in file):
                return False
            else:
                return True
    return False


def get_vod_stream(id):
    VOD_URL = f'https://dce-frontoffice.imggaming.com/api/v3/stream/vod/{id}?includePlaybackDetails=URL'
    headers = compile_headers(auth=True)
    response = requests.get(VOD_URL, headers=headers)
    if response.status_code == 403:
        return False
    if response.status_code != 200:
        print(response.status_code)
        login()
        return get_vod_stream(id)#Retry request, only if relogin passes
    callback_url = response.json()['playerUrlCallback']
    
    response = requests.get(callback_url, headers=headers)
    hls_url = response.json()['hls'][0]['url']
    return hls_url

def get_playlist_ids(id):
    PLAYLIST_URL = f'https://dce-frontoffice.imggaming.com/api/v4/playlist/{id}?bpp=undefined&rpp=250&displaySectionLinkBuckets=HIDE&displayEpgBuckets=HIDE&displayEmptyBucketShortcuts=SHOW'
    headers = compile_headers(auth=True)
    response = requests.get(PLAYLIST_URL, headers=headers)
    if response.status_code == 403:
        return False
    if response.status_code != 200:
        login()
        return get_playlist_ids(id)
    playlist = response.json()
    vods = playlist['vods']
    id_list = []
    for vod in vods:
        if vod['type'] == 'VOD':
            id_list.append(vod['id'])
    print(id_list)
    return id_list

def login():
    LOGIN_URL = 'https://dce-frontoffice.imggaming.com/api/v2/login'
    headers = compile_headers(auth=False)

    credentials = {'id': 'jackmassey2000@gmail.com', 'secret': 'Jackson123123!'}

    response = requests.post(LOGIN_URL, headers=headers, json=credentials)
    if response.status_code != 201:
        print(response)
        print(response.status_code)
        print(response.json())
        print('[ERROR] Could not log in')
        exit()

    res_json = response.json()
    global AUTH_TOKEN
    global REFRESH_TOKEN
    AUTH_TOKEN = res_json['authorisationToken']
    REFRESH_TOKEN = res_json['refreshToken']

def process_downloads(id_list):
    list_len = len(id_list)
    index = 1
    for id in id_list:
        print(f'Processing VOD: {id} - {index}/{list_len}')
        hls_url = get_vod_stream(id)
        event_meta = get_vod_meta(id, hls_url)
        if hls_url and event_meta:
            if not download_all(hls_url, event_meta):
                id_list.append(id)
                print(f'Rescheduled download: {id}')
            else:
                print(f'Finished downloading {id}\n\n')
            index += 1
        else:
            print(f'[ERROR] Failed to get vod stream {id}')

def main(id):
    global START_TIME
    START_TIME = time.time()

    id_list = [id]
    if not get_vod_stream(id): #If input is not a stream, it is likely a playlist, if not, the script will fail
        id_list = get_playlist_ids(id)
    process_downloads(id_list)

    time_elapsed = time.time() - START_TIME
    time_elapsed_string = strftime('%H:%M:%S', localtime(time_elapsed))
    print(f'Finished downloading {len(id_list)} vods in {time_elapsed_string}')


if __name__ == '__main__':
    args = sys.argv
    if len(args) <= 2:
        print('Usage: python main.py <vod_id> (Optional: <output_directory>)')
        exit()
    login()

    id = args[1]
    if len(args) == 3:
        OUTPUT_DIRECTORY = args[2]
        if OUTPUT_DIRECTORY[-1] != '/':
            OUTPUT_DIRECTORY += '/'
        print(f'Setting output directory: {OUTPUT_DIRECTORY}')

        main(id)

'''