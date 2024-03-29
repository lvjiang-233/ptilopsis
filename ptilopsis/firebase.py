from . import config
from .utils.decorators import async_wrap

import json
import firebase_admin
from firebase_admin import credentials, firestore

# stole from https://github.com/y-young/nazurin/blob/master/nazurin/database/firebase.py

class Firebase(object):
    """Firestore driver of Firebase."""
    def __init__(self):
        """Load credentials and initialize Firebase app."""
        cert = config.GOOGLE_CERT
        if cert.startswith('{'):
            cert = json.loads(cert)
        cred = credentials.Certificate(cert)
        if len(firebase_admin._apps) == 0:
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def collection(self, key):
        self._collection = self.db.collection(str(key))
        return self

    def document(self, key=None):
        self._document = self._collection.document(str(key))
        return self

    @async_wrap
    def get(self):
        return self._document.get().to_dict()

    @async_wrap
    def exists(self):
        return self._document.get().exists

    @async_wrap
    def insert(self, key, data):
        if key:
            return self._collection.document(str(key)).set(data)
        else:
            return self._collection.add(data)

    @async_wrap
    def update(self, data):
        return self._document.update(data)

    @async_wrap
    def delete(self):
        return self._document.delete()

