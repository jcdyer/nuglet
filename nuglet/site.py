from contextlib import closing
import itertools

import flask

from nuglet.models import Photo
from nuglet.db import connect

app = flask.Flask('nuglet')

db = connect()

PAGE_SIZE = 100


def render_image(im):
    return '''
        <li>
            <h3>{title}</h3>
            <img alt='{title}' src='{url}' width='600'>
        </li>
        '''.format(title=im['title'], url=im['url'])

def by_page(results, page):
    return itertools.islice(results, PAGE_SIZE * page, PAGE_SIZE * (page + 1))


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
    page = int(flask.request.args.get('page', 1))
    query = 'SELECT * FROM photo WHERE favorites == ?'
    with closing(db.cursor()) as cursor:
        cursor.execute(query, count)
        rows = cursor.fetchall()
        rowcount = len(rows)
        paginators = []
        if page != 1:
            paginators.append('<a href="?page={}">Prev</a>'.format(page - 1))
        if rowcount > page * 100:
            paginators.append('<a href="?page={}">Next</a>'.format(page + 1))
        return '''<h1>Favorites ({} votes)</h1><ol>{}</ol><p>{}</p>'''.format(
            count,
            '\n'.join(render_image(row) for row in by_page(rows, page - 1)),
            ' | '.join(paginators),
        )


if __name__ == '__main__':
    app.run(host='0.0.0.0')
