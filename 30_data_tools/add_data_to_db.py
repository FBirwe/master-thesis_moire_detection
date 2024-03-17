import sqlite3
from helper import load_dotenv, get_relevant_data_dirs
from get_labelstudio_data import get_moires_of_project 
import re
from datetime import datetime
from file_interaction import get_data_files


def add_unknown_pdfs( all_files, con ):
    # alle pdf-files queuen
    pdf_files = []
    for filepath,storage_type in all_files:
        parts = str(filepath).split('/')
        parent_dir = parts[-2]
        filename = parts[-1]
        suffix = filename.split('.')[-1].lower()
    
        if parent_dir == 'pdf' and suffix == 'pdf':
            pdf_files.append((filepath, storage_type))
            
    # pdf_files aus db laden
    c = con.cursor()
    c.execute("SELECT filename,job FROM pdf_page")
    
    db_data = c.fetchall()
    c.close()

    # unbekannte pdfs filtern
    unknown_pdfs = []
    for pdf,storage_type in pdf_files:
        parts = str(pdf).split('/')
        job_name = parts[-3]
        filename = parts[-1]
        filename = re.sub(r'\.pdf$','', filename)
        filename = re.sub(r'\.PDF$','', filename)
    
        file_entry = (
            filename,
            job_name
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

    print(f"successfully added { len(value_lines) } pdfs")


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

def add_related_file( job, pdf_filename, variant_name, type_name, filename ):
    config = load_dotenv()

    with sqlite3.connect( config['DB_PATH'] ) as con:
        try:
            c = con.cursor()
            sql_string = f'''
                INSERT INTO related_file (job,pdf_filename,variant_name,type,filename)
                VALUES ('{ job }','{ pdf_filename }','{ variant_name }','{ type_name }','{ filename }')
            '''
            c.execute( sql_string )
            c.close()
            con.commit()
        except:
            pass


def add_related_files( all_files, con ):
    related_files = []
    error_paths = []
    added_related_files = []
    
    for filepath,storage_type in all_files:
        filepath = str(filepath)
        filepath = filepath[filepath.index('data'):]
           
        try:
            parts = str(filepath).split('/')
            job = parts[1]
            variant_name = parts[2]
            filename = parts[3]
            res = re.match(r'(.+)\.(.+?)\.(.+?)$', filename)
            
            if res and variant_name != 'pdf' and filename != '.DS_Store':               
                related_files.append({
                    'job' : job,
                    'variant_name' : variant_name,
                    'filename' : filename,
                    'filepath' : filepath,
                    'storage_type' : storage_type,
                    'pdf_filename' : res.groups()[0],
                    'type_name' : res.groups()[1]
                })
        except:
            error_paths.append(filepath)
    
    # Varianten hinzufügen
    variants = list(set([rf['variant_name'] for rf in related_files]))
    add_variants( variants, con )

    # duplikate herausfiltern
    c = con.cursor()
    for rf in related_files:        
        if res:
            sql_string = f'''
                SELECT 1 AS status FROM related_file
                WHERE
                    variant_name='{ rf["variant_name"] }' AND
                    pdf_filename='{ rf["pdf_filename"] }' AND
                    job='{ rf["job"] }' AND
                    "type"='{ rf["type_name"] }'
            '''
            c.execute(sql_string)

            result = c.fetchone()
            entry_in_db = result is not None
                        
            if entry_in_db == False:     
                add_related_file( rf["job"], rf["pdf_filename"], rf["variant_name"], rf["type_name"], rf["filename"] )
                added_related_files.append( (rf["job"], rf["pdf_filename"], rf["pdf_filename"], rf["type_name"], rf["filename"]) )
    
    c.close()
    
    print(f"successfully added { len(added_related_files) } related files")


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
    all_files = get_data_files()
    all_files = [af for af in all_files if '.DS_Store' not in str(af[0])]

    con = sqlite3.connect( config['DB_PATH'] )

    add_unknown_pdfs( all_files, con )
    add_related_files( all_files, con )
    # add_moires(
    #     config['LABEL_STUDIO_PROJECT_ID'],
    #     config['LABEL_STUDIO_TOKEN'],
    #     con
    # )


if __name__ == '__main__':
    main()