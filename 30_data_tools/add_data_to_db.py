import sqlite3
from helper import load_dotenv, get_relevant_data_dirs
from get_labelstudio_data import get_moires_of_project 
import re
from collections import Counter
import json
from datetime import datetime


def add_unknown_pdfs( data_dirs, con ):
    # alle pdf-files queuen
    pdf_files = []
    for ddir in data_dirs:
        pdf_files += list( ddir.glob('./pdf/*.pdf'))

    # pdf_files aus db laden
    c = con.cursor()
    c.execute("SELECT filename,job FROM pdf_page")

    db_data = c.fetchall()
    c.close()

    # unbekannte pdfs filtern
    unknown_pdfs = []
    for pdf in pdf_files:
        file_entry = (
            pdf.name.replace(pdf.suffix,''),
            pdf.parent.parent.name
        )

        if file_entry not in db_data:
            unknown_pdfs.append(file_entry)

    # hinzufügen
    import_timestamp = datetime.utcnow()

    value_lines = [
        f'("{ fe[0] }","{ fe[1] }", "{ import_timestamp }")'
        for fe in unknown_pdfs
    ]

    if len( value_lines ) > 0:
        c = con.cursor()
        c.execute(
            f'''
                INSERT INTO pdf_page (filename,job,import_timestamp)
                VALUES { ",".join(value_lines) }
            '''
        )
        c.close()
        con.commit()


def add_variants( variants, con ):
    c = con.cursor()
    c.execute('SELECT name from variant')
    available_variants = [res[0] for res in c.fetchall()]

    variants_to_insert = [v for v in variants if v not in available_variants]
    value_lines = [f'("{ v }")' for v in variants_to_insert]

    if len(value_lines) > 0:
        c.execute(
            f'''
                INSERT INTO variant ('name')
                VALUES { ",".join(value_lines) }
            '''
        )

    c.close()
    con.commit()


def add_related_files( data_dirs, con ):
    related_files = []
    for ddir in data_dirs:
        for sd in ddir.iterdir():
            if sd.is_dir() and sd.name != 'pdf':
                related_files += [f for f in sd.iterdir() if f.name != '.DS_Store']

    # Varianten herausfiltern
    variants = list(set([f.parent.name for f in related_files]))
    add_variants( variants, con )

    # related_file tabelle laden
    c = con.cursor()
    c.execute('''
        SELECT variant_name,pdf_filename,job,type,filename
        FROM related_file
    ''')
    available_data = c.fetchall()
    c.close()

    # related files hinzufügen
    data_to_add = []

    for rf in related_files:
        res = re.match(r'(.+)\.(.+?)$', rf.name.replace(rf.suffix,''))

        if res:
            file_entry = (
                rf.parent.name,
                res.groups()[0],
                rf.parent.parent.name,
                res.groups()[1],
                rf.name
            )

            if file_entry not in available_data:
                data_to_add.append(file_entry)

    value_lines = [
        f'("{ fe[0] }","{ fe[1] }","{ fe[2] }","{ fe[3] }","{ fe[4] }")'
        for fe in data_to_add
    ]

    if len(value_lines) > 0:
        c = con.cursor()
        c.execute(
            f'''
                INSERT INTO related_file (variant_name,pdf_filename,job,type,filename)
                VALUES { ",".join(value_lines) }
            '''
        )
        c.close()
        con.commit()


def add_moires( project_id, ls_token, con ):
    moires = get_moires_of_project( project_id )
    moires_values_to_process = []

    for m in moires:
        res = re.match(r'^(.+?)\.(.+?)\.(.+)\.(.+)\.(.+)$', m['img_name'])
        if res:
            job, variant_name, pdf_name, rf_type, extension = res.groups()

            moires_values_to_process.append((
                pdf_name,job,m['id'],m['rectanglelabels'][0],variant_name
            ))

    # in DB schreiben
    c = con.cursor()
    c.execute('''
        SELECT filename,job,idx,variant FROM moire
    ''')
    available_moires = c.fetchall()
    c.close()

    value_lines = [
        f'("{ v[0] }","{ v[1] }","{ v[2] }","{ v[3] }","{ v[4] }")'
        for v in moires_values_to_process if v not in available_moires
    ]

    if len(value_lines) > 0:
        try:
            SQL = f'''
                INSERT INTO moire (filename,job,idx,"type",variant)
                VALUES { ",".join(value_lines) }
            '''

            c = con.cursor()
            c.execute(SQL)
            c.close()
            con.commit()
        except:
            for l in value_lines:
                try:
                    SQL = f'''
                        INSERT INTO moire (filename,job,idx,"type",variant)
                        VALUES { l }
                    '''

                    c = con.cursor()
                    c.execute(SQL)
                    c.close()
                    con.commit()
                except:
                    pass

def main():
    config = load_dotenv()
    data_dirs = get_relevant_data_dirs()
    con = sqlite3.connect( config['DB_PATH'] )

    add_unknown_pdfs( data_dirs, con )
    add_related_files( data_dirs, con )
    add_moires(
        config['LABEL_STUDIO_PROJECT_ID'],
        config['LABEL_STUDIO_TOKEN'],
        con
    )


if __name__ == '__main__':
    main()