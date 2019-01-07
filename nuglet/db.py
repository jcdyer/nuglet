import os
import sqlite3

DBFILE = 'nuglet2018.db'

def dbexists() -> bool:
    '''Returns True if the database exists'''
    return os.path.exists(DBFILE)

def connect() -> sqlite3.Connection:
    '''Returns a connection to the DB'''
    conn = sqlite3.connect(DBFILE)
    conn.row_factory = sqlite3.Row
    return conn
