import os
import sqlite3

DBFILE = 'nuglet.db'

def dbexists():
    '''Returns True if the database exists'''
    return os.path.exists(DBFILE)

def connect():
    '''Returns a connection to the DB'''
    conn = sqlite3.connect(DBFILE)
    conn.row_factory = sqlite3.Row
    return conn

