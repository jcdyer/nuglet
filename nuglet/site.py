import flask
from nuglet.models import Photo
from nuglet.db import connect

app = flask.Flask('nuglet')

db = connect()

@app.route('/')
def main_page(request):
    query = '''SELECT favorites, count(*) FROM photos GROUP BY favorites'''
    with db.cursor() as cursor:
        cursor.execute(query)
        return [(int(x[0]), int(x[1])) for x in cursor.fetchmany()]

if __name__ == '__main__':
    app.run()
                 
