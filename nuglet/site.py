# pylint: disable=missing-docstring

from collections import OrderedDict
from contextlib import closing
import itertools
from typing import Iterable, TypeVar

import flask

from nuglet.models import Photo
from nuglet.db import connect

PAGE_SIZE: int = 20

T = TypeVar('T')

db = connect()  # pylint: disable=invalid-name
app = flask.Flask('nuglet')  # pylint: disable=invalid-name


class JSONEncoder(flask.json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Photo):
            return obj.to_dict()
        try:
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return super().default(obj)


app.json_encoder = JSONEncoder


def by_page(results: Iterable[T], page: int) -> Iterable[T]:
    return itertools.islice(results, PAGE_SIZE * page, PAGE_SIZE * (page + 1))


def list_context(results):
    page: int = int(flask.request.args.get('page', 1))
    paginators = OrderedDict()
    rowcount = len(results)
    if page != 1:
        paginators['prev'] = '?page={}'.format(page - 1)
    if rowcount > page * PAGE_SIZE:
        paginators['next'] = '?page={}'.format(page + 1)
    return {
        'paginators': paginators,
        'results': by_page((Photo.from_dbrow(result) for result in results), page - 1),
        'page': page,
        'page_count': (rowcount + PAGE_SIZE - 1) // PAGE_SIZE,
        'page_size': PAGE_SIZE,
    }


@app.route('/')
def main_page() -> flask.Response:
    query = '''
        SELECT favorites, count(*) AS count
        FROM photo
        WHERE date >= "2016-11-01"
        AND date < "2017-11-01"
        GROUP BY favorites
    '''

    with closing(db.cursor()) as cursor:
        cursor.execute(query)
        tiers = cursor.fetchall()
    context = {'tiers': tiers}
    return flask.render_template('main_page.html.j2', **context)


@app.route('/favorites')
def all_favorites():
    photoquery = '''
        SELECT * FROM photo
            WHERE favorites > 0
            AND date >= "2016-11-01"
            AND date < "2017-11-01"
            ORDER BY date
    '''
    memberquery = 'SELECT * FROM member'
    with closing(db.cursor()) as cursor:
        cursor.execute(photoquery)
        photos = cursor.fetchall()
        cursor.execute(memberquery)
        members = {m['nsid']: m['username'] for m in cursor.fetchall()}
    context = list_context(photos)
    context['title'] = "Favorites (All photos with votes)"
    context['members'] = members
    context['votes'] = None
    return flask.render_template('list_page.html.j2', **context)


@app.route('/favorites/<votes>')
def favorites(votes):
    photoquery = '''
        SELECT * FROM photo
            WHERE favorites == ?
            AND date >= "2016-11-01"
            AND date < "2017-11-01"
            ORDER BY date
    '''
    memberquery = 'SELECT * FROM member'
    with closing(db.cursor()) as cursor:
        cursor.execute(photoquery, (votes,))
        photos = cursor.fetchall()
        cursor.execute(memberquery)
        members = {m['nsid']: m['username'] for m in cursor.fetchall()}
    context = list_context(photos)
    context['title'] = "Favorites ({} votes)".format(votes)
    context['members'] = members
    context['votes'] = votes
    return flask.render_template('list_page.html.j2', **context)


@app.route('/api/members')
def members_api():
    memberquery = 'SELECT * FROM member'
    with closing(db.cursor()) as cursor:
        cursor.execute(memberquery)
        members = {m['nsid']: m['username'] for m in cursor.fetchall()}
    response = {'members': members}
    return flask.jsonify(response)


@app.route('/api/favorites/<votes>')
def favorites_api(votes):
    photoquery = '''
        SELECT * FROM photo
            WHERE favorites == ?
            AND date >= "2016-11-01"
            AND date < "2017-11-01"
            ORDER BY date
    '''
    with closing(db.cursor()) as cursor:
        cursor.execute(photoquery, (votes,))
        photos = cursor.fetchall()
    response = list_context(photos)
    response['title'] = "Favorites ({} votes)".format(votes)
    return flask.jsonify(**response)


@app.route('/static/<path:path>')
def staticfiles(path):
    return flask.send_from_directory('static', path)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
