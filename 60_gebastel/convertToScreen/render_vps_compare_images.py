from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv, get_pdf_page_processing_status
from file_interaction import get_related_filepath, upload_file, download_blob
from add_data_to_db import add_related_file
from render_screen_images import generate_screen
from random import shuffle
from pathlib import Path
import pandas as pd


def process_separations( separation_to_process ):
    config = load_dotenv()
    variant_name = 'ps2400dpi150lpi'
    data = get_pdf_page_processing_status( variant_name, separation_to_process )
    data_to_update = data.loc[data.file_available == False]
    temp_files = []


    for i in tqdm(range(data_to_update.shape[0])):
        row = data_to_update.iloc[i]
        jpg_file_name = f'{row.filename}.4c.jpg'
        res = get_related_filepath( row.job, f'halftone{ config["LOFI_DPI"] }dpi', jpg_file_name )

        if res:
            img_path, storage_type = res


            if storage_type == 'local':
                img_path = Path( img_path )
            else:
                temp_img_path = config['TEMP_PROCESSING_DIR'] / jpg_file_name
                with temp_img_path.open('wb') as f:
                    f.write(download_blob( img_path ).getbuffer())

                temp_files.append(temp_img_path)
                img_path = temp_img_path


            cyan_path = config['TEMP_PROCESSING_DIR'] / f'{row.filename}.C.tif'
            magenta_path = config['TEMP_PROCESSING_DIR'] / f'{row.filename}.M.tif'
            yellow_path = config['TEMP_PROCESSING_DIR'] / f'{row.filename}.Y.tif'
            black_path = config['TEMP_PROCESSING_DIR'] / f'{row.filename}.K.tif'
            temp_files += [cyan_path, magenta_path, yellow_path, black_path]
            blob_prefix_path = f'data/{ row.job }/{ variant_name }/'


            generate_screen(
                img_path.resolve(),
                cyan_path.resolve(),
                magenta_path.resolve(),
                yellow_path.resolve(),
                black_path.resolve()
            )

            # upload nach azure
            upload_file( cyan_path, blob_prefix_path )
            upload_file( magenta_path, blob_prefix_path )
            upload_file( yellow_path, blob_prefix_path )
            upload_file( black_path, blob_prefix_path )

            # Datei in DB einfügen
            add_related_file( row.job, row.filename, variant_name, 'C', cyan_path.name )
            add_related_file( row.job, row.filename, variant_name, 'M', magenta_path.name )
            add_related_file( row.job, row.filename, variant_name, 'Y', yellow_path.name )
            add_related_file( row.job, row.filename, variant_name, 'K', black_path.name )

    # temp Ordner aufräumen
    for f in temp_files:
        f.unlink()


def main():
    for sep in ['C','M','Y','K']:
        process_separations( sep )

 
if __name__ == "__main__":
    main()