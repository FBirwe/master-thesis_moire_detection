import sys
sys.path.append('../../30_data_tools/')
sys.path.append('../process_masks/')

import numpy as np
import cv2
import random
import pandas as pd
from tqdm.auto import tqdm
import pickle
import json
import sqlite3
from file_interaction import upload_buffer
from generic_image_db_interaction import save_generic_image
from helper import load_dotenv, get_pdf_page_processing_status
from get_labelstudio_data import get_moires_of_project, get_results_of_project

from mask_functions import get_config as get_mask_config, load_masks, get_whole_mask
from pattern_creation import get_pattern_style, get_pattern_img_by_style
from file_interaction import get_related_filepath, open_img, download_blob
from io import BytesIO

dotenv = load_dotenv()
mask_config = get_mask_config()


DEBUG = False
N = 50

def get_pdf_pages():
    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        pdf_pages = pd.merge(
            pd.read_sql(
                '''
                    SELECT p.*, ifnull(gi.times_used, 0) AS times_used FROM pdf_page p
                    LEFT JOIN (
                        SELECT gi.job, gi.pdf_filename AS filename, count(*) AS times_used FROM generic_image gi
                        GROUP BY gi.job, gi.pdf_filename
                    ) gi ON p.job = gi.job AND p.filename = gi.filename
                    WHERE p.job = '24-03-05-01_randomTrainPages'
                ''',
                con
            ),
            get_pdf_page_processing_status(
                'halftone600dpi',
                '4c'
            ).loc[
                :,
                ['filename','job','file_available']
            ],
            how='left',
            on=['job','filename']
        ).rename(columns={'file_available':'halftone_available'})

        pdf_pages = pd.merge(
            pdf_pages,
            get_pdf_page_processing_status(
                'halftone600dpi',
                'masks'
            ).loc[
                :,
                ['filename','job','file_available']
            ],
            how='left',
            on=['job','filename']
        ).rename(columns={'file_available':'masks_available'})


        pdf_pages = pdf_pages.loc[
            (pdf_pages.halftone_available) &
            (pdf_pages.masks_available)
        ]

    return pdf_pages


def log( message ):
    if DEBUG:
        print( message )


def get_next_idx_for_image( row, method ):
    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        c = con.cursor()
        c.execute(
            f'''
                SELECT IFNULL(max(idx),0) + 1 AS next_idx FROM generic_image gi 
                WHERE 
                    job='{ row.job }' AND 
                    pdf_filename = '{ row.filename }' AND 
                    variant_name = 'halftone{ dotenv["LOFI_DPI"]}dpi' AND 
                    "type" = '4c' AND 
                    "method" = '{ method }' 
            '''
        )

        return_value = c.fetchone()[0]
        c.close()

    return return_value


def get_random_masks( masks, weights, k ):
    out = []

    while len(out) < k and len(out) < len(masks):
        next_item = random.choices(
            masks,
            weights= weights,
            k=1
        )[0]

        if next_item['bbox'] not in [el['bbox'] for el in out]:
            out.append(next_item)

    return out


def main():
    config_name = sys.argv[1]
    N = int(sys.argv[2])

    with open(f'./configurations/{ config_name }.json') as config_file:
        config = json.load(config_file)

    pdf_pages = get_pdf_pages()

    for j in tqdm(range(N)):
        page_row = pdf_pages.sample(n=1, weights=pdf_pages.times_used.max() - pdf_pages.times_used + 1).iloc[0]
        
        img_path = get_related_filepath(
            page_row.job,
            f'halftone{ dotenv["LOFI_DPI"] }dpi',
            f'{ page_row.filename }.4c.jpg'
        )
        
        masks_path = get_related_filepath(
            page_row.job,
            f'halftone{ dotenv["LOFI_DPI"] }dpi',
            f'{ page_row.filename }.masks.pkl'
        )
        
        masks = load_masks( masks_path )
        img = np.array(open_img( img_path ))
        
        # zu verarbeitende Masken auswählen
        relevant_masks = get_random_masks(
            masks,
            [m['area'] * m['stability_score'] for m in masks],
            config['masks_per_generated_image']
        )
        rows_of_image = []
        
        for i in range(len(relevant_masks)):
            m = relevant_masks[i]
        
            # Wenn Verarbeitungs- und Halbtonauflösung abweichen
            # wird die Maske entsprechend skaliert
            if config['processing_dpi'] != dotenv["LOFI_DPI"]:
                mask_scale_factor = config['processing_dpi'] / dotenv["LOFI_DPI"]
                m['mask'] = (cv2.resize(
                    (m['mask'] * 255).astype('uint8'),
                    (0,0),
                    fx=mask_scale_factor,
                    fy=mask_scale_factor
                ) / 255).round().astype('bool')
                m['bbox'] = [int(val * mask_scale_factor) for val in m['bbox']]
                
            
            # die verwendeten Anpassungen werden ausgewählt
            row = {
                'config_name' : config['config_name'],
                'job' : page_row.job,
                'pdf_filename' : page_row.filename,
                'method' : 'soft_light', #'screen' if random.random() > 0.5 else 'multiply',
                'ssim' : -1,
                'bbox' : m['bbox'],
                'overlay_intensity_C' : config['overlay_intensity'][0],
                'overlay_intensity_M' : config['overlay_intensity'][1],
                'overlay_intensity_Y' : config['overlay_intensity'][2],
                'overlay_intensity_K' : config['overlay_intensity'][3],
                'K_mean_coverage' : img[:,:,3][m['bbox'][1]:m['bbox'][1]+m['bbox'][3],m['bbox'][0]:m['bbox'][0]+m['bbox'][2]][m['mask']].mean() / 255,
                'K_std_coverage' : img[:,:,3][m['bbox'][1]:m['bbox'][1]+m['bbox'][3],m['bbox'][0]:m['bbox'][0]+m['bbox'][2]][m['mask']].std() / 255
            }
            row['idx'] = get_next_idx_for_image( page_row, row['method'] )
            
            pattern_style = get_pattern_style(config, m)

            for key in pattern_style:
                row[key] = pattern_style[key]

            rows_of_image.append(row)

        # Dateien ablegen
        dir_name = f'{ row["job"] }_{ row["pdf_filename"] }_{ row["idx"] }'.replace('.','_')
        dir_path = dotenv['TEMP_PROCESSING_DIR'] / 'musterueberlagerung_batches' / 'ausgehend' / dir_name

        dir_path.mkdir( exist_ok=True, parents=True )

        with ( dir_path / img_path[0].split('/')[-1] ).open('wb') as img_file:
            img_file.write( download_blob(img_path[0]).getbuffer() )

        with ( dir_path / masks_path[0].split('/')[-1] ).open('wb') as mask_file:
            pickle.dump(relevant_masks, mask_file)



        with ( dir_path / 'data.json' ).open('w') as rows_json_file:
            json.dump(
                {
                    'rescale_factor' : config['processing_dpi'] / dotenv["LOFI_DPI"],
                    'processing_dpi' : config['processing_dpi'],
                    'pattern_mask' : config['pattern_mask'],
                    'equal_brightness' : config['equal_brightness'],
                    'soft_light' : config['soft_light'],
                    'rows' : rows_of_image
                },
                rows_json_file
            )

if __name__ == '__main__':
    main()