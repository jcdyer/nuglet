"""
Get favorited nuglet pictures from the flickr api
"""

# pylint: disable=invalid-name, missing-docstring

import base64
import configparser
import contextlib
from datetime import datetime
import hashlib
import hmac
import logging
import time
import uuid
import urllib

import progressbar
import requests

from .db import connect, dbexists
from .models import Member, Photo

logger = logging.getLogger(__name__)


config = configparser.ConfigParser()
config.read('data/apikey.txt')

DBFILE = 'data/nuglet{}.db'.format(datetime.now().year)
FLICKR_CREDS = dict(config['flickr'])
GROUP_NAME = 'Nuglet and Chitlin'


def load_token_string():
    token_string = urllib.parse.urlencode({'oauth_token': '72157675659595285-4b0681164e04c840', 'oauth_token_secret': 'e4eceb66070d9b74', 'user_nsid': '51949548@N02', 'username': 'Cliff Dyer'})
    return token_string


def get_base_string(request):
    params = urllib.parse.urlencode(sorted(request.params.items()))
    return '&'.join([
        request.method,
        urllib.parse.quote_plus(request.url),
        urllib.parse.quote_plus(params),
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
    logger.info("Requesting token")
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
    logger.info("Requesting access token with rt {} and verifier {}".format(request_token, verifier))
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
    logger.debug("SBS %s", get_base_string(req))
    sign_request(req, token_secret=access_token['oauth_token_secret'][0])
    return req.prepare()


def debug_request(req):
    print(dir(req))
    logger.debug("REQUEST")
    logger.debug(req.url)
    #logger.debug(get_base_string(req))


def debug_response(resp):
    logger.debug("RESPONSE")
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
    debug_response(rt_response)
    request_token = urllib.parse.parse_qs(rt_response.text)

    print(
        'Please authenticate with Flickr: {}?oauth_token={}'.format(
            'https://www.flickr.com/services/oauth/authorize',
            request_token['oauth_token'][0]
        )
    )
    verifier = input("What was the verification code? ").strip()

    req = build_access_token_request(request_token, verifier)
    at_response = session.send(req)
    debug_response(at_response)
    return at_response.text


def get_group_id_by_name(groups, name):
    for group in groups['groups']['group']:
        print(group['name'])
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

            if photo['datetaken'] < '2017-11-01' or photo['datetaken'] > '2018-11-01':
                yield None  # This keeps the progress bar accurate
                continue
            req = api_request(
                'flickr.photos.getFavorites',
                access_token,
                api_key=FLICKR_CREDS['key'],
                photo_id=photo['id']
            )

            try:
                favs_for_photo = session.send(req).json()
            except:
                logger.warning("No response for {}".format(req.url))
                favs_for_photo = {'photo': {'person': ErrorCollection([])}}
            yield Photo.from_api(photo, favs_for_photo)

        page += 1

class ErrorCollection(list):
    def __len__(self):
        return -1

def iter_by_favorites(photos):
    for best in sorted(photos, key=(lambda ph: -ph.favorites)):
        yield best


def get_access_token(session):
    token_string = load_token_string() or authenticate(session)
    access_token = urllib.parse.parse_qs(token_string)
    return access_token


def create_db(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photo (
            nsid VARCHAR(255),
            owner VARCHAR(255),
            title VARCHAR(255),
            format VARCHAR(255),
            date VARCHAR(255),
            url VARCHAR(255),
            favorites INTEGER(8)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS member (
            nsid VARCHAR(255),
            username VARCHAR(255)
        )
    """)


def store_members_in_db(cursor, members):
    cursor.executemany(
        "INSERT INTO MEMBER (nsid, username) VALUES (?, ?)",
        ((m.nsid, m.username) for m in members)
    )
def store_in_db(cursor, photos):
    cursor.executemany(
        "INSERT INTO photo VALUES (?, ?, ?, ?, ?, ?, ?)",
        ((p.nsid, p.owner, p.title, p.format, p.date, p.url, p.favorites) for p in photos)
    )

def iter_existing_photos(cursor):
    cursor.execute("SELECT nsid FROM photo")
    for photo in cursor:
        yield photo['nsid']

def fetch_member_response(session, access_token, group_id):
    req = api_request(
        'flickr.groups.members.getList',
        access_token,
        api_key=FLICKR_CREDS['key'],
        group_id=group_id,
    )
    debug_request(req)
    response = session.send(req)
    debug_response(response)
    print(response)
    print(response.text)
    return response.json()

def iter_members(member_response):
    for member in member_response['members']['member']:
        yield Member.from_api(member)

def main_members():
    session = requests.Session()
    access_token = get_access_token(session)
    print("Access token", access_token)
    req = api_request(
        'flickr.people.getGroups',
        access_token,
        api_key=FLICKR_CREDS['key'],
        user_id=access_token['user_nsid'][0],
    )
    groups_response = session.send(req).json()
    print(groups_response)
    group_id = get_group_id_by_name(groups_response, GROUP_NAME)
    member_response = fetch_member_response(session, access_token, group_id)
    members = iter_members(member_response)
    db = connect()
    if dbexists():
        existing_photos = set()
        with contextlib.closing(db.cursor()) as cursor:
            create_db(cursor)
            db.commit()
    with contextlib.closing(db.cursor()) as cursor:
        store_members_in_db(cursor, members)
        db.commit()

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
    group_id = get_group_id_by_name(groups_response, GROUP_NAME)

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

    newdb = not dbexists()
    db = connect()
    print(newdb)

    # is this backwards?
    if newdb:
        existing_photos = set()
        with contextlib.closing(db.cursor()) as cursor:
            create_db(cursor)
            db.commit()
    else:
        with contextlib.closing(db.cursor()) as cursor:
            existing_photos = set(iter_existing_photos(cursor))

    with contextlib.closing(db.cursor()) as cursor:
        for photo in iter_by_favorites(photo for photo in photos if photo):
            store_in_db(cursor, [photo])
        db.commit()


def test_signature():
    req = requests.Request(
        'GET',
        'https://www.flickr.com/services/oauth/request_token',
        params={
            'oauth_nonce': '89601180',
            'oauth_timestamp': '1305583298',
            'oauth_consumer_key': '653e7a6ecc1d528c516cc8f92cf98611',
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_version': '1.0',
            'oauth_callback': 'http://www.example.com',
        }
    )
    assert get_base_string(req) == 'GET&https%3A%2F%2Fwww.flickr.com%2Fservices%2Foauth%2Frequest_token&oauth_callback%3Dhttp%253A%252F%252Fwww.example.com%26oauth_consumer_key%3D653e7a6ecc1d528c516cc8f92cf98611%26oauth_nonce%3D95613465%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1305586162%26oauth_version%3D1.0'


if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    main_members()
