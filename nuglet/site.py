# pylint: disable=missing-docstring

from collections import OrderedDict
from contextlib import closing
import itertools

import flask

from nuglet.models import Photo
from nuglet.db import connect

PAGE_SIZE = 100

db = connect()  # pylint: disable=invalid-name
app = flask.Flask('nuglet')  # pylint: disable=invalid-name


def by_page(results, page):
    return itertools.islice(results, PAGE_SIZE * page, PAGE_SIZE * (page + 1))

def list_context(results):
    page = int(flask.request.args.get('page', 1))
    paginators = OrderedDict()
    rowcount = len(results)
    if page != 1:
        paginators['prev'] = '?page={}'.format(page - 1)
    if rowcount > page * PAGE_SIZE:
        paginators['next'] = '?page={}'.format(page + 1)
    return {
        'paginators': paginators,
        'results': by_page((Photo.from_dbrow(result) for result in results), page - 1),
    }


@app.route('/')
def main_page():
    query = 'SELECT favorites, count(*) as count FROM photo GROUP BY favorites'
    with closing(db.cursor()) as cursor:
        cursor.execute(query)

        return '''<h1>Favorite photos</h1><ul>{}</ul>'''.format(
            '\n'.join(
                '<h3><a href="/favorites/{favorites}">{favorites} votes ({count} images)</a></h3>'.format(**x)
                for x in cursor.fetchall()
            )
        )

@app.route('/favorites/<count>')
def favorites(count):
    photoquery = '''
        SELECT * FROM photo
            WHERE favorites == ?
            ORDER BY date
    '''
    memberquery = 'SELECT * FROM member'
    with closing(db.cursor()) as cursor:
        cursor.execute(photoquery, count)
        photos = cursor.fetchall()
        cursor.execute(memberquery)
        members = {m['nsid']: m['username'] for m in cursor.fetchall()}
    context = list_context(photos)
    context['title'] = "Favorites ({} votes)".format(count)
    context['members'] = members
    return flask.render_template('list_page.html.j2', **context)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
