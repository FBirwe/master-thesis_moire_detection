import subprocess
from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from datetime import datetime
import pandas as pd
from file_interaction import get_generic_image_filepath, upload_file, download_blob, get_blobs
from generic_image_db_interaction import get_generic_images
import re


def generate_screen( halftone_path, cyan_path, magenta_path, yellow_path, black_path ):
    res = subprocess.run(
        f'osascript ./generate_screen.sctp "{ halftone_path }" "{ cyan_path }" "{ magenta_path }" "{ yellow_path }" "{ black_path }"',
        shell=True,
        capture_output=True
    )


def get_images_to_process( config ):
    data = get_generic_images()
    all_files = get_blobs( filter='generic_data/')
    file_map = {}

    for f in all_files:
        res = re.match(r'.+/(.+?)\.(.+\.p\d+)\.(.+?)\.(.+?)\.(\d+)\..+', f)

        if res:
            cur_level = file_map
            groups = res.groups()
            
            for i in range(len(groups)):
                if groups[i] not in cur_level:
                    if i < len(groups) -1:
                        cur_level[groups[i]] = {}
                    else:
                        cur_level[groups[i]] = []

                cur_level = cur_level[groups[i]]

            cur_level.append(f)

    def row_is_in_file_map( row ):
        if row.job not in file_map:
            return False

        if row.pdf_filename not in file_map[row.job]:
            return False

        if f"halftone{ config['LOFI_DPI'] }dpi" not in file_map[row.job][row.pdf_filename]:
            return False
        
        if row.method not in file_map[row.job][row.pdf_filename][f"halftone{ config['LOFI_DPI'] }dpi"]:
            return False
        
        if str(row.idx) not in file_map[row.job][row.pdf_filename][f"halftone{ config['LOFI_DPI'] }dpi"][row.method]:
            return False
        
        return True

    
    images_to_process = []
    for i in tqdm(range(data.shape[0])):
        row = data.iloc[i]

        if row_is_in_file_map(row):            
            halftone_available = (len([
                af for af in file_map[row.job][row.pdf_filename][f"halftone{ config['LOFI_DPI'] }dpi"][row.method][str(row.idx)]
                if f"{ row.job }.{ row.pdf_filename }.halftone{ config['LOFI_DPI'] }dpi.{ row.method }.{ row.idx }.jpg" in af
            ]) > 0)
            black_available = (len([
                af for af in file_map[row.job][row.pdf_filename][f"halftone{ config['LOFI_DPI'] }dpi"][row.method][str(row.idx)]
                if f"{ row.job }.{ row.pdf_filename }.halftone{ config['LOFI_DPI'] }dpi.{ row.method }.{ row.idx }.K" in af
            ]) > 0)
            
            if halftone_available and black_available == False:
                images_to_process.append( row.name )

    return data.loc[
        data.index.isin( images_to_process )
    ]


def main():
    config = load_dotenv()
    images_to_process = get_images_to_process( config )

    print( 'started' )

    for i in tqdm(range(images_to_process.shape[0])):
        temp_files = []
        row = images_to_process.iloc[i]
        res = get_generic_image_filepath( row.pdf_filename, row.job, row.method, row.idx )
        
        if res:
            img_path, storage_type = res
            jpg_file_name = img_path.split('/')[-1]

            temp_img_path = config['TEMP_PROCESSING_DIR'] / jpg_file_name
            with temp_img_path.open('wb') as f:
                f.write(download_blob( img_path ).getbuffer())

            temp_files.append(temp_img_path)
            img_path = temp_img_path

            cyan_path = config['TEMP_PROCESSING_DIR'] / f'{ jpg_file_name.replace(".jpg","") }.C.tif'
            magenta_path = config['TEMP_PROCESSING_DIR'] / f'{ jpg_file_name.replace(".jpg","") }.M.tif'
            yellow_path = config['TEMP_PROCESSING_DIR'] / f'{ jpg_file_name.replace(".jpg","") }.Y.tif'
            black_path = config['TEMP_PROCESSING_DIR'] / f'{ jpg_file_name.replace(".jpg","") }.K.tif'
            temp_files += [cyan_path, magenta_path, yellow_path, black_path]
            blob_prefix_path = 'generic_data/'


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

            # temp Ordner aufräumen
            for f in temp_files:
                f.unlink()

 
if __name__ == "__main__":
    main()