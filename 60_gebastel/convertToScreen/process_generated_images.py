from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from PIL import Image
from datetime import datetime
import pandas as pd
import numpy as np
from generic_image_db_interaction import get_generic_images
from file_interaction import get_blobs, get_generic_image_filepath, download_blob, upload_buffer
from io import BytesIO
import re

SEPARATIONS = ['C','M','Y','K']

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
            screen_4c_available = (len([
                af for af in file_map[row.job][row.pdf_filename][f"halftone{ config['LOFI_DPI'] }dpi"][row.method][str(row.idx)]
                if f"{ row.job }.{ row.pdf_filename }.halftone{ config['LOFI_DPI'] }dpi.{ row.method }.{ row.idx }.4c_{ config['LOFI_DPI'] }.jpg" in af
            ]) > 0)
            black_available = (len([
                af for af in file_map[row.job][row.pdf_filename][f"halftone{ config['LOFI_DPI'] }dpi"][row.method][str(row.idx)]
                if f"{ row.job }.{ row.pdf_filename }.halftone{ config['LOFI_DPI'] }dpi.{ row.method }.{ row.idx }.K" in af
            ]) > 0)
            
            if black_available and screen_4c_available == False:
                images_to_process.append( row.name )

    return data.loc[
        data.index.isin( images_to_process )
    ]



def generate_4c_images( data_to_update ):
    Image.MAX_IMAGE_PIXELS = None
    dotenv = load_dotenv()
    target_dpi = dotenv["LOFI_DPI"]
    type_name = f'4c_{ target_dpi }'

    for i in tqdm(range(data_to_update.shape[0])):
        row = data_to_update.iloc[i]

        out_filename = f'{ row.job }.{ row.pdf_filename }.{ row.variant_name }.{ row.method }.{ row.idx }.{ type_name }.jpg'
        out_path = f'generic_data/{ out_filename }'
        target_size = None 
        cmyk_img = None
        
        for i in range(len(SEPARATIONS)):
            c = SEPARATIONS[i]

            res = get_generic_image_filepath(
                row.pdf_filename,
                row.job,
                row.method,
                row.idx,
                variant=c
            )

            if res:
                separation_img_path, storage_type = res

                if storage_type == 'azure':
                    img = Image.open( download_blob( separation_img_path ) )
                else:
                    img = Image.open( separation_img_path )

                if target_size is None:
                    target_size = (
                        int(round(img.size[0] / 2400 * target_dpi)),
                        int(round(img.size[1] / 2400 * target_dpi))
                    )
                    cmyk_img = np.zeros((target_size[1], target_size[0], 4)).astype('uint8')
            
                img = img.convert('L').resize(
                    target_size,
                    resample=Image.Resampling.BICUBIC
                )
                cmyk_img[:,:,i] = np.array(img)
                img.close()

        if target_size is not None:
            imagefile = BytesIO()
            Image.fromarray(255 - cmyk_img, mode="CMYK").save( imagefile, format='JPEG', dpi=(target_dpi, target_dpi), progressive=True )

            # buffer hochladen
            upload_buffer(
                imagefile.getvalue(),
                out_path
            )


def main():
    dotenv = load_dotenv()
    data_to_update = get_images_to_process( dotenv )

    generate_4c_images( data_to_update )


if __name__ == '__main__':
    main()