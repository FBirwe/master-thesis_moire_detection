from pathlib import Path
from helper import load_dotenv
import sqlite3
import shutil
from tqdm import tqdm

def main():
    config = load_dotenv()
    con = sqlite3.connect( config['DB_PATH'] )

    c = con.cursor()
    c.execute(
        f'''
            SELECT variant_name,pdf_filename,job,filename FROM related_file
            WHERE "type"="4c_{ config['LOFI_DPI'] }"
        '''
    )
    rfs = c.fetchall()
    rfs = [
        {
            'variant_name' : rf[0],
            'pdf_filename' : rf[1],
            'job' : rf[2],
            'filename' : rf[3]
        }
        for rf in rfs
    ]
    c.close()

    for rf in tqdm(rfs):
        source_file = config['DATA_DIR'] / rf['job'] / rf['variant_name'] / rf['filename']
        target_file_name = f'{ rf["job"]}.{ rf["variant_name"] }.{ rf["filename"] }'
        target_file = config['LABEL_STUDIO_DIR'] / target_file_name
        
        if source_file.exists() and target_file.exists() == False:
            shutil.copy(
                source_file,
                target_file
            )

if __name__ == '__main__':
    main()