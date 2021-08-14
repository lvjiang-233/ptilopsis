from . import config
from .firebase import Firebase

import os
import time
import aiohttp
import aiofiles
from urllib.parse import urlencode, quote

import logging

class OneDriveManager(object):
    db = Firebase()
    collection = db.collection(config.FIREBASE_NAME)
    initialize = True

    access_token = None
    refresh_token = None
    expires_at = 0
    folder_path = None

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.document = self.collection.document(user_id)

    async def init(self) -> bool:
        user_token_info = await self.document.get()
        if user_token_info:
            self.access_token = user_token_info['access_token']
            self.refresh_token = user_token_info['refresh_token']
            self.expires_at = user_token_info['expires_at']
            self.folder_path = user_token_info['folder_path']
            if self.expires_at < time.time():
                await self.refresh_token_by_refresh_token()
            return True
        else:
            return False

    async def folder_path_validation(self) -> bool:
        # https://docs.microsoft.com/zh-cn/graph/api/driveitem-get?view=graph-rest-1.0&tabs=http
        # by path
        if self.folder_path != '':
            api = 'https://graph.microsoft.com/v1.0/me/drive/root:' + self.folder_path
            r = await self._request('GET', api)
            if 'error' in r.keys():
                return False
            return True
        else:
            return False

    @staticmethod
    def generate_login_url(user_id: int) -> str:
        # https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow#request-an-authorization-code
        endpoint = r'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        scope = ['Files.Read.All', 'Files.ReadWrite.All', 'offline_access']
        # considering webhook_url end with `/`
        redirect_uri = config.WEBHOOK_URL + config.REDIRECT_PATH.strip('/')
        queries = {
            'client_id' : config.CLIENT_ID,
            'response_type' : 'code',
            'response_mode' : 'query',
            'redirect_uri' : redirect_uri,
            'scope': ' '.join(scope),
            'state': user_id
        }
        # method `quote` will encode space to `%20` rather than `+` encoded by `quote_plus`
        # but `urlencode` default to use `quote_plus`
        return endpoint + '?' + urlencode(queries, quote_via=quote)

    @staticmethod
    async def get_token_by_auth_code(auth_code: str, user_id: int):
        # https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow#request-an-authorization-code
        endpoint = f'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        # considering webhook_url end with `/`
        redirect_uri = config.WEBHOOK_URL + config.REDIRECT_PATH.strip('/')
        header = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'client_id': config.CLIENT_ID,
            'client_secret': config.CLIENT_SECRET,
            'code': auth_code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        async with aiohttp.request('POST', url=endpoint, headers=header, data=urlencode(data)) as resp:
            r = await resp.json()
            try:
                user_token_info = {
                    'access_token': r['access_token'],
                    'refresh_token': r['refresh_token'],
                    'expires_at': time.time() + r['expires_in'],
                    'folder_path': ''
                }
                document = Firebase().collection(config.FIREBASE_NAME).document(user_id)
                if not await document.exists():
                    await document.insert(user_id, user_token_info)
                else:
                    await document.update(user_token_info)
            except Exception as error:
                logging.error(error)

    async def refresh_token_by_refresh_token(self):
        endpoint = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        header = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'client_id': config.CLIENT_ID,
            'client_secret': config.CLIENT_SECRET,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        async with aiohttp.request('POST', url=endpoint, headers=header, data=urlencode(data)) as resp:
            r = await resp.json()
            try:
                self.access_token = r['access_token']
                self.refresh_token = r['refresh_token']
                self.expires_at = time.time() + r['expires_in']
                await self.document.update({
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'expires_at': self.expires_at,
                    'folder_path': self.folder_path
                    })
            except:
                logging.error(r)

    async def set_folder_path(self, folder_path: str) -> bool:
        folder_path = folder_path.rstrip('/')
        if folder_path.startswith('/'):
            self.folder_path = folder_path
            r = await self.folder_path_validation()
            if r:
                user_token_info:dict = await self.document.get()
                user_token_info['folder_path'] = folder_path
                await self.document.update(user_token_info)
            return r
        else:
            return False

    async def upload(self, file_path:str):
        file_name = file_path.split('/')[-1]
        file_size = os.path.getsize(file_path)

        #create_file_api = 'https://graph.microsoft.com/v1.0/me/drive/root:' + self.folder_path + ':/children'
        #body = {
        #    "name": file_name,
        #    "size": file_size,
        #    "file": {},
        #    "@microsoft.graph.conflictBehavior": "rename"
        #}
        #create_r = await self._request('POST', create_file_api, json=body)

        create_session_api = 'https://graph.microsoft.com/v1.0/me/drive/root:' + self.folder_path + f'/{file_name}' + ':/createUploadSession'#.format(item_id=create_r['id'])
        session_r = await self._request('POST', create_session_api)

        header = {
            'Content-Range': 'bytes 0-{end}/{size}'.format(end=file_size - 1,
                                                           size=file_size)
        }
        async with aiofiles.open(file_path, mode='rb') as data:
            await self._request('PUT',
                                session_r['uploadUrl'],
                                headers=header,
                                data=await data.read())


    async def _request(self, method: str, url: str, headers=None, data=None, json=None):
        _headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + self.access_token,
        }
        if headers is not None:
            _headers.update(headers)
        if data is None:
            _headers['Content-Type'] = 'application/json'

        async with aiohttp.request(method, url, headers=_headers, data=data, json=json) as resp:
            if 'application/json' in resp.headers['Content-Type']:
                    return await resp.json()
            return await resp.text()
