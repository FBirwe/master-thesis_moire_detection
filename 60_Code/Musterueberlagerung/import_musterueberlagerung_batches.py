import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from file_interaction import upload_file
from generic_image_db_interaction import save_generic_image
import json
import sqlite3
from tqdm import tqdm


"""
    Importiert die durch "musterueberlagerung.py" erzeugten synthetischen Moirés
    in die Datenbanl
"""


def get_generic_image_name( job, pdf_filename, method, processing_dpi, next_idx ):
    return f"{ job }.{ pdf_filename }.halftone{ processing_dpi }dpi.{ method }.{ next_idx }.jpg"

def img_exists_in_db( job, pdf_filename, method, idx ):
    dotenv = load_dotenv()

    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        c = con.cursor()
        c.execute(
            f'''
                SELECT * FROM generic_image
                WHERE
                    job='{ job }' AND
                    pdf_filename='{ pdf_filename }' AND
                    method='{ method }' AND
                    idx={ idx }
            '''
        )
        res = c.fetchone()

        c.close()

    return (res is None) == False


def import_image( batch_path ):
    with ( batch_path / 'data.json' ).open() as json_file:
        data = json.load( json_file )

    img_name = get_generic_image_name(
        data['rows'][0]['job'],
        data['rows'][0]['pdf_filename'],
        data['rows'][0]["method"],
        data['processing_dpi'],
        data['rows'][0]["idx"]
    )
    img_path = batch_path / img_name

    if img_path.exists() == False and ( batch_path / 'synthetic_moire.jpg').exists():
        ( batch_path / 'synthetic_moire.jpg').rename( img_path )

    generic_img_exists = img_path.exists()
    img_already_in_db = img_exists_in_db(
        data['rows'][0]['job'],
        data['rows'][0]['pdf_filename'],
        data['rows'][0]["method"],
        data['rows'][0]["idx"]
    )

    if generic_img_exists and img_already_in_db == False:
        upload_file(
            img_path,
            'generic_data/'
        )
        
        # bild in DB ablegen
        save_generic_image(
            data['rows']
        )
        

if __name__ == '__main__':
    dotenv = load_dotenv()
    batches_dir = dotenv['TEMP_PROCESSING_DIR'] / 'musterueberlagerung_batches' / 'eingehend'
    batches = [entry for entry in batches_dir.iterdir() if entry.is_dir()]

    for batch in tqdm( batches ):
        import_image( batch )