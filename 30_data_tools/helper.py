import shutil
from tqdm import tqdm
from dotenv import dotenv_values
from pathlib import Path
import pandas as pd
import json
import re
import sqlite3
import os


def get_pdf_page_processing_status( variant_name, type_name ):
    config = load_dotenv()
    con = sqlite3.connect( config['DB_PATH'] )

    data_overview = pd.read_sql(
        f'''
            SELECT pp.*, IFNULL(rf.file_available, 0) file_available FROM pdf_page pp 
            LEFT JOIN (
            	SELECT *, 1 AS file_available FROM related_file rf 
            	WHERE rf.variant_name='{ variant_name }' AND "type" = '{ type_name }'
            ) rf
            ON pp.filename = rf.pdf_filename AND pp.job = rf.job
        ''',
        con
    )
    data_overview.loc[:,'file_available'] = data_overview.loc[:,'file_available'] == 1
    con.close()

    return data_overview


def load_moires_from_json( con ):
    with get_labeling_data_file().open() as jf:
        data = json.load(jf)

    # job data laden
    c = con.cursor()
    c.execute('''
        SELECT filename,job
        FROM pdf_page
    ''')

    file_job_con = {d[0]:d[1] for d in c.fetchall()}
    c.close()

    found_moires = []
    total_count = 0

    for d in data:
        for a in d['annotations']:
            if 'result' in a:
                for entry in a['result']:
                    if entry['type'] == 'rectanglelabels':
                        total_count += 1
                        
                        filename = d['file_upload']
                        splitted = filename.split('_#_')
                        
                        job = None
                        if len(splitted) > 1:
                            job = splitted[0]
                            filename = splitted[1]
                                                
                        res = re.match(r'(.{8})-(.+)\..+\.jpg', filename)
                        
                        if res:
                            _, pdf_name = res.groups()
                            idx = entry['id']
                            
                            if job == None and pdf_name in file_job_con:
                                job = file_job_con[pdf_name]
                            
                            # value to pixel
                            for key in ['x','y','width','height']:
                                if key in entry['value']:
                                    if key in ['x','width']:
                                        entry['value'][key] = entry['value'][key] / 100 * entry['original_width']
                                    else:
                                        entry['value'][key] = entry['value'][key] / 100 * entry['original_height']

                            if job != None:
                                found_moires.append((
                                    pdf_name,
                                    job,
                                    idx,
                                    entry['value']
                                ))

    return found_moires


def is_supported_file_type( file, extensions ):
    if len(extensions) == 0:
        return True

    return file.suffix in extensions

def move_all_files( from_dir, to_dir, extensions=[] ):
    all_files = [f for f in from_dir.iterdir() if f.is_file()]

    for f in tqdm( all_files ):
        if is_supported_file_type( f, extensions ):
            target_file = to_dir / f.name

            shutil.move( f, target_file )


def load_dotenv():
    script_file_path = Path(  __file__ ).parent
    config = dict(dotenv_values( Path(__file__).parent / ".env" ))
    config['DATA_DIRS'] = [(script_file_path / data_path).resolve() for data_path in config['DATA_DIRS'].split(';')]
    config['TEMP_PROCESSING_DIR'] = Path(config['TEMP_PROCESSING_DIR'])
    config['GENERIC_DATA_DIR'] = (script_file_path / config['GENERIC_DATA_DIR']).resolve()
    # config['GENERIC_GENERATED_DATA_DIR'] = config['GENERIC_DATA_DIR'] / '01_generated_data'
    # config['GENERIC_INFORMATION_DATA_DIR'] = config['GENERIC_DATA_DIR'] / '02_information_data'
    # config['GENERIC_LABELSTUDIO_DATA_DIR'] = config['DATA_DIR'] / '11_labelstudio_generic_data'
    config['MODEL_DIR'] = (script_file_path / config['MODEL_DIR']).resolve()
    config['PATTERN_DIR'] = (script_file_path / config['PATTERN_DIR']).resolve()
    # config['SORT_DIR'] = config['DATA_DIR'] / config['SORT_DIR']
    config['DB_PATH'] = script_file_path / config['DB_PATH']
    config['LABELING_JSON_PATH'] = Path( config['LABELING_JSON_PATH'] )
    config['LOFI_DPI'] = int(config['LOFI_DPI'])
    config['LOFI_SCREEN_DPI'] = int(config['LOFI_SCREEN_DPI'])
    config['TRAIN_DATA_DPI'] = int(config['TRAIN_DATA_DPI'])
    # config['LABEL_STUDIO_DIR'] = config['DATA_DIR'] / config['LABEL_STUDIO_DIR']
    config['LABEL_STUDIO_DB_PATH'] = Path( config['LABEL_STUDIO_DB_PATH'] )
    config['AZURE_CONNECTION_STRING'] = f'DefaultEndpointsProtocol=https;AccountName={ config["AZURE_ACCOUNT_NAME"] };AccountKey={ config["AZURE_ACCOUNT_KEY"] };EndpointSuffix=core.windows.net'
    os.environ['TESSDATA_PREFIX'] = str(Path( config['TESSDATA_PREFIX'] ).resolve())

    return config


def get_labeling_data_file():
    config = load_dotenv()
    json_files = list( config['LABELING_JSON_PATH'].glob('./*.json') )
    
    if len(json_files) == 0:
        raise "no labeling data available"

    return sorted(
        json_files,
        key=lambda entry: entry.stat().st_ctime,
        reverse=True
    )[0]


def get_relevant_data_dirs( ):
    config = load_dotenv()
    IGNORE_DIRS = [
        config['SORT_DIR']
    ]

    normal_data_dir = [ddir for ddir in config['DATA_DIR'].iterdir() if ddir.is_dir() and ddir not in IGNORE_DIRS]
    generic_data_dir = [config['GENERIC_GENERATED_DATA_DIR']]

    return normal_data_dir + generic_data_dir


if __name__ == '__main__':
    config = load_dotenv()
    con = sqlite3.connect( config['DB_PATH'] )
    print(load_moires_from_json(con))