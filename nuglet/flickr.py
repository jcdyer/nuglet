"""
Get favorited nuglet pictures from the flickr api
"""

# pylint: disable=invalid-name, missing-docstring

import base64
import configparser
import contextlib
import hashlib
import hmac
import logging
import time
import uuid
import urllib

import progressbar
import requests

from .db import connect, dbexists
from .models import Photo

logger = logging.getLogger(__name__)


config = configparser.ConfigParser()
config.read('apikey.txt')

DBFILE = 'nuglet.db'
FLICKR_CREDS = dict(config['flickr'])


def load_token_string():
    return 'fullname=&oauth_token=72157675659595285-4b0681164e04c840&oauth_token_secret=e4eceb66070d9b74&user_nsid=51949548%40N02&username=Cliff%20Dyer'  # pylint: disable=line-too-long


def get_base_string(request):
    params = urllib.parse.urlencode(sorted(request.params.items()))
    return '&'.join([
        request.method,
        urllib.parse.quote_plus(request.url),
        urllib.parse.quote_plus(params)
    ])


def sign_request(request, token_secret=''):
    signature = base64.b64encode(
        hmac.new(
            key='&'.join([FLICKR_CREDS['secret'], token_secret]).encode('ascii'),
            msg=get_base_string(request).encode('ascii'),
            digestmod=hashlib.sha1
        ).digest()
    )
    request.params['oauth_signature'] = signature


def build_request_token_request():
    url = 'https://www.flickr.com/services/oauth/request_token'
    req = requests.Request('GET', url, params={
        'oauth_nonce': str(uuid.uuid4()),
        'oauth_timestamp': str(time.time()),
        'oauth_consumer_key': FLICKR_CREDS['key'],
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_version': '1.0',
        'oauth_callback': 'oob',
    })
    sign_request(req)
    return req.prepare()


def build_access_token_request(request_token, verifier):
    url = 'https://www.flickr.com/services/oauth/access_token'
    req = requests.Request('GET', url, params={
        'oauth_nonce': str(uuid.uuid4()),
        'oauth_timestamp': str(time.time()),
        'oauth_verifier': verifier,
        'oauth_consumer_key': FLICKR_CREDS['key'],
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_version': '1.0',
        'oauth_token': request_token['oauth_token'][0],
    })
    sign_request(req, token_secret=request_token['oauth_token_secret'][0])
    return req.prepare()


def api_request(method, access_token, **params):
    """method is the api command (like flickr.groups.getInfo), not the HTTP method"""
    params.update({
        'nojsoncallback': '1',
        'format': 'json',
        'method': method,
        'oauth_nonce': str(uuid.uuid4()),
        'oauth_timestamp': str(time.time()),
        'oauth_consumer_key': FLICKR_CREDS['key'],
        'oauth_token': access_token['oauth_token'][0],
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_version': '1.0',
    })
    req = requests.Request('GET', 'https://api.flickr.com/services/rest', params=params)
    # debug_request(req)
    sign_request(req, token_secret=access_token['oauth_token_secret'][0])
    return req.prepare()


def debug_request(req):
    logger.debug(get_base_string(req))
    logger.debug(req.url)


def debug_response(resp):
    logger.debug(resp.headers)
    logger.debug(resp.text)


def authenticate(session):
    """
    Return an access token.

    Fields:
      * fullname
      * oauth_token
      * oauth_token_secret
      * user_nsid
      * username
    """
    req = build_request_token_request()
    rt_response = session.send(req)
    request_token = urllib.parse.parse_qs(rt_response.text)

    print(
        'Please authenticate with Flickr: {}?oauth_token={}'.format(
            'https://www.flickr.com/services/oauth/authorize',
            request_token['oauth_token'][0]
        )
    )
    input('then press <Enter>')
    verifier = input("What was the verification code?")

    req = build_access_token_request(request_token, verifier)
    at_response = session.send(req)
    return at_response.text


def get_group_id_by_name(groups, name):
    for group in groups['groups']['group']:
        if group['name'] == name:
            return group['nsid']


def iter_group_photos(session, access_token, group_id):
    page = 1
    page_count = 1

    while page <= page_count:
        req = api_request(
            'flickr.groups.pools.getPhotos',
            access_token,
            api_key=FLICKR_CREDS['key'],
            group_id=group_id,
            extras='date_taken,url_o,original_format',
            page=page,
            per_page=250,
        )
        photos_in_group = session.send(req).json()
        page_count = photos_in_group['photos']['pages']

        for photo in photos_in_group['photos']['photo']:
            req = api_request(
                'flickr.photos.getFavorites',
                access_token,
                api_key=FLICKR_CREDS['key'],
                photo_id=photo['id']
            )

            favs_for_photo = session.send(req).json()
            yield Photo.from_api(photo, favs_for_photo)

        page += 1


def iter_by_favorites(photos):
    for best in sorted(photos, key=(lambda ph: -ph.favorites)):
        yield best


def get_access_token(session):
    token_string = load_token_string() or authenticate(session)
    access_token = urllib.parse.parse_qs(token_string)
    return access_token


def create_db(cursor):
    cursor.execute("""
        CREATE TABLE photo (
            nsid VARCHAR(255),
            owner VARCHAR(255),
            title VARCHAR(255),
            format VARCHAR(255),
            date VARCHAR(255),
            url VARCHAR(255),
            favorites INTEGER(8)
        )
    """)


def store_in_db(cursor, photos):

    cursor.executemany(
        "INSERT INTO photo VALUES (?, ?, ?, ?, ?, ?, ?)",
        ((p.nsid, p.owner, p.title, p.format, p.date, p.url, p.favorites)
         for p in photos)
    )

def iter_existing_photos(cursor):
    cursor.execute("SELECT nsid FROM photo")
    for photo in cursor:
        yield photo['nsid']

def get_members():
    session = requests.Session()
    access_token = get_access_token(session)
    req = api_request(
        'flickr.people.getGroups',
        access_token,
        api_key=FLICKR_CREDS['key'],
        user_id=access_token['user_nsid'][0],
    )
    groups_response = session.send(req).json()
    group_id = get_group_id_by_name(groups_response, "Li'l Nuglet")
    req = api_request(
        'flickr.groups.members.getList',
        access_token,
        api_key=FLICKR_CREDS['key'],
        group_id=group_id,
    )
    return session.send(req).json()

def main():
    session = requests.Session()
    access_token = get_access_token(session)

    req = api_request(
        'flickr.people.getGroups',
        access_token,
        api_key=FLICKR_CREDS['key'],
        user_id=access_token['user_nsid'][0],
    )
    groups_response = session.send(req).json()
    group_id = get_group_id_by_name(groups_response, "Li'l Nuglet")
    req = api_request(
        'flickr.groups.getInfo',
        access_token,
        api_key=FLICKR_CREDS['key'],
        group_id=group_id,
    )
    group_info_response = session.send(req).json()
    total = int(group_info_response['group']['pool_count']['_content'])
    progress = progressbar.ProgressBar(max_value=total)
    photos = progress(iter_group_photos(session, access_token, group_id))

    newdb = dbexists()
    db = connect()

    if newdb:
        existing_photos = set()
        with contextlib.closing(db.cursor()) as cursor:
            create_db(cursor)
            db.commit()
    else:
        with contextlib.closing(db.cursor()) as cursor:
            existing_photos = set(iter_existing_photos(cursor))

    with contextlib.closing(db.cursor()) as cursor:
        for photo in iter_by_favorites(photos):
            store_in_db(cursor, [photo])
        db.commit()


if __name__ == '__main__':
    logging.basicConfig(level='INFO')
    main()
