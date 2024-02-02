from PIL import Image
Image.MAX_IMAGE_PIXELS = 2351589062
import numpy as np
from helper import load_dotenv
from pathlib import Path
import re
from tqdm import tqdm
import pandas as pd
import sqlite3
import sys

SEPARATIONS = ['C','M','Y','K']

def get_unprocessed_files( data_dir, target_dpi, con ):
    data = pd.read_sql(
        f'''
            SELECT rfvps.*, ifnull(rffc.fc_available,0) AS fc_available FROM (
                SELECT variant_name, pdf_filename, job, 1 AS "fc_available" FROM related_file rf 
                WHERE "type" = "4c_{ target_dpi }"
            ) rffc
            FULL OUTER JOIN (
                SELECT variant_name, pdf_filename, job, count(*) >= 1 AS vps_available FROM related_file rf 
                WHERE "type" IN ("C","M","Y","K")
                GROUP BY variant_name, pdf_filename, job
            ) rfvps
            ON rffc.variant_name = rfvps.variant_name AND rffc.pdf_filename = rfvps.pdf_filename AND rffc.job = rfvps.job
        ''',
        con
    )
    data.vps_available = data.vps_available == 1
    data.fc_available = data.fc_available == 1

    relevant_data = data[data.fc_available == False]
    relevant_data = relevant_data.sample(frac=1)

    files = {}

    for _,row in relevant_data.iterrows():
        variant_dir = data_dir / row.job / row.variant_name
        current_files = list( variant_dir.glob(f'./{ row.pdf_filename }*.tiff') )

        for c in current_files:
            if c.exists():
                sep = c.name.strip(c.suffix).split('.')[-1]
                if  sep in ['C','M','Y','K','SF1','SF2']:
                    if row.pdf_filename not in files:
                        files[row.pdf_filename] = {}

                    files[row.pdf_filename][sep] = c

    return files


def create_4c_tiff( tiff_collection, target_dpi ):
    Image.MAX_IMAGE_PIXELS = None            
    target_size = None 
    cmyk_img = None
    
    for i in range(len(SEPARATIONS)):
        c = SEPARATIONS[i]

        if c in tiff_collection:
            img = Image.open( tiff_collection[c] )

            if target_size is None:
                target_size = (
                    int(round(img.size[0] / 2400 * target_dpi)),
                    int(round(img.size[1] / 2400 * target_dpi))
                )
                cmyk_img = np.ones((target_size[1], target_size[0], 4)).astype('uint8')
        
            img = img.convert('L').resize(
                target_size,
                resample=Image.Resampling.BICUBIC
            )
            cmyk_img[:,:,i] = np.array(img)
            img.close()

    if target_size is not None:
        return Image.fromarray(255 - cmyk_img, mode="CMYK")
    
    return None



# def create_4c_tiff( tiff_collection ):
#     separations = [
#         'C',
#         'M',
#         'Y',
#         'K'
#     ]

#     out_img = np.zeros(1)
#     for i in range(len(separations)):
#         sep = separations[i]
#         try:
#             img = Image.open( tiff_collection[sep] )

#             if len(out_img.shape) == 1:
#                 out_img = np.ones(( img.size[1], img.size[0], 4))
            
#             out_img[:,:,i] = img

#             img.close()
#         except:
#             pass

#     out_img = 1 - out_img
#     out_img *= 255
#     out_img = out_img.astype('uint8')

#     return Image.fromarray(
#         out_img,
#         mode="CMYK"
#     )


def main():
    config = load_dotenv()
    con = sqlite3.connect( config['DB_PATH'] )
    dry_run = False

    if len(sys.argv) > 1:
        dry_run = sys.argv[1] == "--dry_run"

    unprocessed_files = get_unprocessed_files(config['DATA_DIR'], config["LOFI_SCREEN_DPI"], con)

    for key in tqdm(unprocessed_files):
        if dry_run:
            print( key )
        else:
            try:
                uf = unprocessed_files[key]

                img = create_4c_tiff(uf, config['LOFI_SCREEN_DPI'])
                out_path = uf[list(uf.keys())[0]].parent / f'{key}.4c_{ config["LOFI_SCREEN_DPI"] }.jpg'
                img.save(
                    out_path,
                    progressive=True,
                    dpi=( config['LOFI_SCREEN_DPI'], config['LOFI_SCREEN_DPI'] )
                )
                img.close()
            except Exception as e:
                print( key )
                print( e.message )


if __name__ == '__main__':
    main()