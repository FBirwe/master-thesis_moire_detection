import sqlite3
from helper import load_dotenv
from datetime import datetime

def save_old_db( db_path ):
    now = datetime.now()
    new_name = f'{ now.strftime("%Y-%m-%d_%H-%M-%S") }_{ db_path.name }'
    target_path = db_path.parent / new_name

    db_path.rename(target_path)


def init():
    config = load_dotenv()

    # alte DB wegspeichern
    save_old_db(config['DB_PATH'])

    con = sqlite3.connect(config['DB_PATH'])
    c = con.cursor()

    # pdf_pages table
    c.execute(
        '''CREATE TABLE pdf_page (
            filename TEXT,
            job TEXT,
            PRIMARY KEY (filename, job)
        )''')

    # moire table
    c.execute(
        '''CREATE TABLE moire (
            filename TEXT,
            job TEXT,
            idx TEXT,
            type TEXT,
            notes TEXT,
            PRIMARY KEY (filename, job, idx)
        )''')

    # variants table
    c.execute(
        '''CREATE TABLE variant (
            name TEXT,
            PRIMARY KEY (name)
        )''')

    # related_files table
    c.execute(
        '''CREATE TABLE related_file (
            variant_name TEXT,
            pdf_filename TEXT,
            job TEXT,
            type TEXT,
            filename TEXT,
            PRIMARY KEY (variant_name, pdf_filename, job, "type")
        )''')

    c.close()
    con.commit()
    con.close()

init()