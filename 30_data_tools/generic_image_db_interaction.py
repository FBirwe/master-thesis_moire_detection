import sys
sys.path.append('../../30_data_tools/')
import pandas as pd
import sqlite3
from datetime import datetime
import uuid
import json
from helper import load_dotenv
from get_labelstudio_data import get_results_of_project
from tqdm import tqdm
import numpy as np


dotenv = load_dotenv()

def get_temp_id():
    myuuid = uuid.uuid4()
    myuuidStr = 'temp_' + str(myuuid)
    
    return myuuidStr


def get_generic_images():
    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        return pd.read_sql(
            'SELECT * FROM generic_image',
            con,
            parse_dates=['timestamp']
        )


def write_generic_image( pdf_filename, job, img_type, variant_name, method, idx ):
    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        c = con.cursor()

        sql_string = f'''
            INSERT INTO generic_image ('pdf_filename','job','type','variant_name','method','idx','timestamp')
            VALUES ('{ pdf_filename }','{ job }','{ img_type }','{ variant_name }','{ method }',{ idx },'{ datetime.now() }')
        '''
        c.execute(sql_string)
        c.close()

        con.commit()


def write_mask( pdf_filename, job, img_type, variant_name, method, idx, mask_id, bbox, ssim, overlay_intensities, pattern, pattern_position ):
    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        c = con.cursor()

        sql_string = f'''
            INSERT INTO mask ('pdf_filename','job','type','variant_name','method','idx','mask_id','bbox','ssim','overlay_intensity_C','overlay_intensity_M','overlay_intensity_Y','overlay_intensity_K','pattern','pattern_position')
            VALUES ('{ pdf_filename }','{ job }','{ img_type }','{ variant_name }','{ method }',{ idx },'{ mask_id }','{ ";".join([str(b) for b in bbox]) }',{ ssim },{ overlay_intensities[0] },{ overlay_intensities[1] },{ overlay_intensities[2] },{ overlay_intensities[3] },'{ pattern }','{ pattern_position[0] };{ pattern_position[1] }')
        '''
        c.execute(sql_string)
        c.close()

        con.commit()


def write_mask_adjustments( pdf_filename, job, img_type, variant_name, method, idx, mask_id, adjustment_name, execution_index, features ):
    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        c = con.cursor()

        sql_string = f'''
            INSERT INTO adjustment_per_mask ("pdf_filename","job","type","variant_name","method","idx","mask_id","adjustment","execution_index","features")
            VALUES ('{ pdf_filename }','{ job }','{ img_type }','{ variant_name }','{ method }',{ idx },'{ mask_id }','{ adjustment_name }',{ execution_index },'{ json.dumps(features) }')
        '''
        c.execute(sql_string)
        c.close()

        con.commit()


def save_generic_image( rows_of_image ):
    job = rows_of_image[0]['job']
    pdf_filename = rows_of_image[0]['pdf_filename']
    method = rows_of_image[0]['method']
    idx = rows_of_image[0]['idx']

    write_generic_image(
        pdf_filename,
        job,
        '4c',
        f'halftone{ dotenv["LOFI_DPI"] }dpi',
        method,
        idx
    )

    for row in rows_of_image:
        mask_id = get_temp_id()

        write_mask(
            pdf_filename,
            job,
            '4c',
            f'halftone{ dotenv["LOFI_DPI"] }dpi',
            method,
            idx,
            mask_id,
            row['bbox'],
            row['ssim'],
            [
                row['overlay_intensity_C'],
                row['overlay_intensity_M'],
                row['overlay_intensity_Y'],
                row['overlay_intensity_K']
            ],
            row['pattern'],
            row['pattern_img_position']
        )

        for i in range(len(row['effects'])):
            effect = row['effects'][i]

            write_mask_adjustments(
                pdf_filename,
                job,
                '4c',
                f'halftone{ dotenv["LOFI_DPI"] }dpi',
                method,
                idx,
                mask_id,
                effect['effect_name'],
                i + 1,
                { key:effect[key] for key in effect if key != 'effect_name' }
            )


def update_temp_masks():
    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        # Masken laden
        masks = pd.read_sql(
            '''
                SELECT * FROM mask m
            ''',
            con
        )
        
        relevant_results = [
            r for r in
            get_results_of_project(2)
            if 'id' in r and r['id'] not in masks.mask_id.unique()
        ]

        
        masks_to_update = masks.loc[
            masks.mask_id.str.match('^temp_.+')
        ].index
        
        # update masken filtern
        requires_update = []
        
        for idx in tqdm(masks_to_update):
            row = masks.loc[idx]
            
            for r in relevant_results:
                filename = f'{ row.job }.{ row.pdf_filename }.{ row.method }.{ row.idx }.4c_{ dotenv["LOFI_DPI"] }.jpg'
                bbox_string = f"{ r['bbox']['x'] };{ r['bbox']['y'] };{ r['bbox']['width'] };{ r['bbox']['height'] }"

                if r['img_name'] == filename and row.bbox == bbox_string:
                    requires_update.append((idx,r['id']))
                    break
                    
        for update_line in tqdm(requires_update):
            row = masks.loc[update_line[0]]

            sql_mask = f'''
                UPDATE mask
                SET mask_id='{ update_line[1] }'
                WHERE (
                    pdf_filename='{ row.pdf_filename }' AND 
                    job='{ row.job }' AND 
                    "type"='{ row['type'] }' AND
                    variant_name='{ row.variant_name }' AND
                    idx={ row.idx } AND
                    mask_id='{ row.mask_id }'
                )
            '''

            sql_adjustments = f'''
                UPDATE adjustment_per_mask
                SET mask_id='{ update_line[1] }'
                WHERE (
                    pdf_filename='{ row.pdf_filename }' AND 
                    job='{ row.job }' AND 
                    "type"='{ row['type'] }' AND
                    variant_name='{ row.variant_name }' AND
                    idx={ row.idx } AND
                    mask_id='{ row.mask_id }'
                )
            '''
            c = con.cursor()
            try:
                c.execute( sql_mask )
                c.execute( sql_adjustments )
            except sqlite3.IntegrityError:
                pass
                
            c.close()
            con.commit()


def load_mask_configuration_file( job, pdf_filename, method, idx, mask_id ):
    dotenv = load_dotenv()
    
    with sqlite3.connect( dotenv['DB_PATH'] ) as con:
        c = con.cursor()
        out = {
            'job' : job,
            'pdf_filename' : pdf_filename,
            'method' : method,
            'idx' : idx,
            'mask_id' : mask_id,
            'effects' : [],
            'effect_order' : []
        }

        c.execute(
            f'''
                SELECT bbox, ssim, overlay_intensity_C, overlay_intensity_M, overlay_intensity_Y, overlay_intensity_K, pattern, pattern_position FROM mask
                WHERE job='{ job }' AND pdf_filename='{ pdf_filename }' AND method='{ method }' AND idx={ idx } AND mask_id='{ mask_id }'
            '''
        )
        # maske laden
        mask = c.fetchone()
        out['bbox'] = [int(val) for val in mask[0].split(';')]
        out['ssim'] = float(mask[1])
        out['overlay_intensity_C'] = float(mask[2])
        out['overlay_intensity_M'] = float(mask[3])
        out['overlay_intensity_Y'] = float(mask[4])
        out['overlay_intensity_K'] = float(mask[5])
        out['pattern'] = mask[6]
        out['pattern_position'] = [int(val) for val in mask[7].split(';')]

        # adjustments laden
        c.execute(
            f'''
                SELECT execution_index, adjustment, features FROM adjustment_per_mask apm 
                WHERE job='{ job }' AND pdf_filename='{ pdf_filename }' AND method='{ method }' AND idx={ idx } AND mask_id='{ mask_id }'
                ORDER BY execution_index ASC
            '''
        )
        adjustments = c.fetchall()

        for _,effect_name,features_string in adjustments:
            out['effect_order'].append(effect_name)
            features = json.loads(features_string)
            features['effect_name'] = effect_name
            out['effects'].append(features)
        
        c.close()

    return out


if __name__ == '__main__':
    update_temp_masks()