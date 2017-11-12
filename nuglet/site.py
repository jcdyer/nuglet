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
    def format_single_row(row):
        row_text = '{favorites} votes ({count} images)'.format(**row)
        return '<h3><a href="/favorites/{favorites}">{}</a></h3>'.format(row_text, **row)

    def format_all_row():
        row_text = 'Any votes'
        return '<h3><a href="/favorites">{}</a></h3>'.format(row_text)

    query = '''
        SELECT favorites, count(*) AS count 
        FROM photo 
        WHERE date >= "2016-11-01" 
        AND date < "2017-11-01" 
        GROUP BY favorites
    '''

    with closing(db.cursor()) as cursor:
        cursor.execute(query)

        all_row = format_all_row()
        rows = (format_single_row(row) for row in cursor.fetchall())
        return '''<h1>Favorite photos</h1><ul>{}</ul>'''.format(
            '\n'.join(itertools.chain([format_all_row()], rows)
            )
        )


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
    context['title'] = "Favorites (All votes)"
    context['members'] = members
    return flask.render_template('list_page.html.j2', **context)

@app.route('/favorites/<count>')
def favorites(count):
    photoquery = '''
        SELECT * FROM photo
            WHERE favorites == ?
            AND date >= "2016-11-01"
            AND date < "2017-11-01" 
            ORDER BY date
    '''
    memberquery = 'SELECT * FROM member'
    with closing(db.cursor()) as cursor:
        cursor.execute(photoquery, (count,))
        photos = cursor.fetchall()
        cursor.execute(memberquery)
        members = {m['nsid']: m['username'] for m in cursor.fetchall()}
    context = list_context(photos)
    context['title'] = "Favorites ({} votes)".format(count)
    context['members'] = members
    return flask.render_template('list_page.html.j2', **context)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
