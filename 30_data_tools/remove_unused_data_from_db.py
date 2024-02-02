import sqlite3
from helper import load_dotenv, get_relevant_data_dirs
from collections import Counter

def remove_related_files( base_dir, con ):
    c = con.cursor()
    c.execute('SELECT * FROM related_file')
    rf = c.fetchall()

    rows_to_delete = []
    for row in rf:
        asset_path = base_dir / row[2] / row[0] / row[4]

        if asset_path.exists() == False:
            rows_to_delete.append(row)

    # delete
    for rd in rows_to_delete:
        c.execute(f'''
            DELETE FROM related_file
            WHERE variant_name="{ rd[0] }" AND  pdf_filename="{ rd[1] }" AND  job="{ rd[2] }" AND  "type"="{ rd[3] }"
        ''')
    c.close()
    con.commit()

    print( f'deleted { len(rows_to_delete) } entries' )


def main():
    dotenv = load_dotenv()
    con = sqlite3.connect( dotenv['DB_PATH'] )

    remove_related_files( dotenv['DATA_DIR'], con )


if __name__ == '__main__':
    main()