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


def load_data( pkl_path ):
    data = pd.read_pickle(pkl_path)
    data.loc[
        :,
        'timestamp'
    ] = datetime.fromtimestamp( int(pkl_path.name.strip(pkl_path.suffix)) )

    return data


def get_temp_id():
    myuuid = uuid.uuid4()
    myuuidStr = 'temp_' + str(myuuid)
    
    return myuuidStr


def filter_already_processed( data, sql_string, con ):
    # bestehende generic images auslesen
    already_processed_df = pd.read_sql( sql_string, con )

    already_processed = []
    for _,row in already_processed_df.iterrows():
        already_processed.append(";".join([str(v) for v in row.values]))

    # relevant rows auf neue limitieren
    return data.loc[
        data.apply(
            lambda row: ";".join([str(v) for v in row.values]),
            axis=1
        ).isin(already_processed) == False
    ]


def write_generic_images( data, con ):
    relevant_rows = data.loc[
        :,
        ['pdf_filename','job','type','variant_name','method','idx','timestamp']
    ].groupby(['pdf_filename','job','type','variant_name','method','idx']).last().reset_index()

    relevant_rows = filter_already_processed(
        relevant_rows,
        '''
            SELECT pdf_filename, job,"type",variant_name,method,idx,timestamp
            FROM generic_image 
        ''',
        con
        
    )
    
    # Bilder schreiben
    sql_lines = [
        f"('{ row.pdf_filename }','{ row.job }','{ row.type }','{ row.variant_name }','{ row.method }',{ row.idx },'{ row.timestamp }')"
        for _,row in relevant_rows.iterrows()
    ]

    if len(sql_lines) > 0:
        SQL = f'''
            INSERT INTO generic_image ('pdf_filename','job','type','variant_name','method','idx','timestamp')
            VALUES { ",".join(sql_lines) }
        '''
        
        c = con.cursor()
        try:
            c.execute(SQL)
        except sqlite3.IntegrityError:
            for l in sql_lines:
                try:
                    SQL = f'''
                        INSERT INTO generic_image ('pdf_filename','job','type','variant_name','method','idx','timestamp')
                        VALUES { l }
                    '''
                    c.execute(l)
                except:
                    pass


def write_masks( data, con ):
    already_processed_masks = pd.read_sql(
        '''
            SELECT
                pdf_filename,
                job,
                "type",
                variant_name,
                method,
                idx,
                bbox as bbox_string,
                1 AS is_already_processed
            FROM mask
        ''',
        con
    )
    already_processed_masks.idx = already_processed_masks.idx.astype('str')

    merged = pd.merge(
        data,
        already_processed_masks,
        how="left",
        on=[
            'pdf_filename',
            'job',
            'type',
            'variant_name',
            'method',
            'idx',
            'bbox_string'
        ]
    )
    merged.is_already_processed = merged.is_already_processed == 1

    sql_lines = [
        f"('{ row.pdf_filename }','{ row.job }','{ row.type }','{ row.variant_name }','{ row.method }',{ row.idx },'{ row['id'] }','{ row.bbox_string }',{ row.ssim },{ row.overlay_intensity_C },{ row.overlay_intensity_M },{ row.overlay_intensity_Y },{ row.overlay_intensity_K })"
        for _,row in merged.loc[merged.is_already_processed == False].iterrows()
    ]

    errors = 0
    if len(sql_lines) > 0:
        SQL = f'''
            INSERT INTO mask ('pdf_filename','job','type','variant_name','method','idx','mask_id','bbox','ssim','overlay_intensity_C','overlay_intensity_M','overlay_intensity_Y','overlay_intensity_K')
            VALUES { ",".join(sql_lines) }
        '''
        
        c = con.cursor()
        try:
            c.execute(SQL)
        except sqlite3.IntegrityError:
            for l in sql_lines:
                try:
                    SQL = f'''
                        INSERT INTO mask ('pdf_filename','job','type','variant_name','method','idx','mask_id','bbox','ssim','overlay_intensity_C','overlay_intensity_M','overlay_intensity_Y','overlay_intensity_K')
                        VALUES { l }
                    '''
                    c.execute(SQL)
                except sqlite3.IntegrityError:
                    errors += 1
        
        
        c.close()
        con.commit()

        print(f"successfully written { (len(sql_lines) - errors) }/{ len(sql_lines) } masks")


def get_features_by_row( row ):
    features = []
    
    if row.use_blow_up_centered:
        features.append((
            'blow_up_centered',
            {
                "centered_c" : row.rotation_degree
            }
        ))

    if row.use_blow_up_region:
        features.append((
            'blow_up_region',
            {
                "blow_up_count" : row.blow_up_count,
                "blow_up_radius" : row.blow_up_radius,
                "blow_up_center" : row.blow_up_center,
                "blow_up_c" : row.blow_up_c,
            }
        ))

    if row.use_contract_region:
        features.append((
            'contract_region',
            {
                "contract_count" : row.contract_count,
                "contract_radius" : row.contract_radius,
                "contract_center" : row.contract_center,
                "contract_c" : row.contract_c,
            }
        ))

    if row.use_contract_centered:
        features.append((
            'contract_centered',
            {
                "centered_c" : row.rotation_degree
            }
        ))

    if row.use_pillow_disortion:
        features.append((
            'pillow_disortion',
            {
                "pillow_depth_x" : row.pillow_depth_x,
                "pillow_depth_y" : row.pillow_depth_y
            }
        ))

    if row.use_roll:
        features.append((
            'roll',
            {
                "pattern_stretch_factor" : row.pattern_stretch_factor
            }
        ))
    
    if row.use_rotation:
        features.append((
            'rotation',
            {
                "rotation_degree" : row.rotation_degree
            }
        ))

    if row.use_scale:
        features.append((
            'scale',
            {
                "scale" : row.scale
            }
        ))


    if row.use_stretch:
        features.append((
            'stretch',
            {
                "stretch_x" : row.stretch_x,
                "stretch_y" : row.stretch_y
            }
        ))


    if row.use_trapezoidal_distortion:
        features.append((
            'trapezoidal_distortion',
            {
                "trapezoidal_distortion_strength_1" : row.trapezoidal_distortion_strength_1,
                "trapezoidal_distortion_strength_2" : row.trapezoidal_distortion_strength_2,
                "trapezoidal_distortion_direction" : row.trapezoidal_distortion_direction
            }
        ))

    if row.use_uniform_trapezoidal_distortion:
        features.append((
            'uniform_trapezoidal_distortion',
            {
                "trapezoidal_distortion_strength" : row.trapezoidal_distortion_strength,
                "trapezoidal_distortion_direction" : row.trapezoidal_distortion_direction
            }
        ))


    if row.use_wave_deform:
        features.append((
            'wave_deform',
            {
                "wave_length" : row.wave_length,
                "wave_depth" : row.wave_depth
            }
        ))

    return features


def get_effect_order(row):
    relevant_columns = sorted([
        c.replace('use_','') for c in row.keys()
        if c.startswith('use_') and row[c] == True
    ])
    
    return relevant_columns


def write_adjustments_per_mask( data, con ):
    relevant_rows = data.loc[
        :,
        [
            'pdf_filename',
            'job',
            'type',
            'variant_name',
            'method',
            'idx',
            'id',
            'bbox_string',
            'ssim',
            'overlay_intensity_C',
            'overlay_intensity_M',
            'overlay_intensity_Y',
            'overlay_intensity_K'
        ]
    ].groupby(['pdf_filename','job','type','variant_name','method','idx','id']).last().reset_index()

    relevant_rows = filter_already_processed(
        relevant_rows,
        '''
            SELECT
                "pdf_filename",
                "job",
                "type",
                "variant_name",
                "method",
                "idx",
                "mask_id",
                "bbox",
                "ssim",
                "overlay_intensity_C",
                "overlay_intensity_M",
                "overlay_intensity_Y",
                "overlay_intensity_K"
            FROM mask
        ''',
        con
    )

    sql_lines = []

    for i in tqdm(range(relevant_rows.shape[0])):
        r = relevant_rows.iloc[i]

        row = data.loc[
            (data.pdf_filename == r.pdf_filename) &
            (data.job == r.job) &
            (data.type == r.type) &
            (data.variant_name == r.variant_name) &
            (data.method == r.method) &
            (data.idx == r.idx) &
            (data.id == r.id)
        ].iloc[0]

        features = get_features_by_row( row )

        if 'effect_order' in data.columns and type(row.effect_order) == list:
            effect_order = row.effect_order
        else:
            effect_order = get_effect_order( row )

        for j in range(len(features)):
            f = features[j]

            sql_lines.append(
                f"('{ row.pdf_filename }','{ row.job }','{ row.type }','{ row.variant_name }','{ row.method }',{ row.idx },'{ row['id'] }','{ f[0] }',{ (effect_order.index(f[0]) + 1) },'{ json.dumps(f[1]) }')"
            )

    SQL = f'''
        INSERT INTO adjustment_per_mask ("pdf_filename","job","type","variant_name","method","idx","mask_id","adjustment","execution_index","features")
        VALUES { ",".join(sql_lines) }
    '''

    c = con.cursor()
    try:
        c.execute(SQL)
    except sqlite3.IntegrityError:
        for l in sql_lines:
            try:
                SQL = f'''
                    INSERT INTO adjustment_per_mask ("pdf_filename","job","type","variant_name","method","idx","mask_id","adjustment","execution_index","features")
                    VALUES { l }
                '''
                c.execute(l)
            except:
                pass

    c.close()
    con.commit()


def load_data_to_process( dotenv ):
    with open('../Musterueberlagerung/config.json') as config_file:
        config = json.load(config_file)

    data = pd.concat([
        load_data(pkl_path) for pkl_path in dotenv['GENERIC_INFORMATION_DATA_DIR'].glob('./*.pkl')
    ]).reset_index().drop(columns=['index'])

    data.loc[:,'job'] = data.img_path.apply(lambda val: val.parent.parent.name)
    data.loc[:,'pdf_filename'] = data.img_path.apply(lambda val: val.name.replace('.4c.jpg',''))
    data.loc[:,'idx'] = data.basic_name.str.extract(r'.+\$PLACEHOLDER\$\.(.+)')
    data.loc[:,'variant_name'] = f'halftone{ dotenv["LOFI_DPI"] }dpi'
    data.loc[:,'type'] = '4c'
    data.loc[:,'img_name'] = data.apply(lambda row: row.basic_name.replace("$PLACEHOLDER$",row.method) + '.' + row["type"] + '.jpg', axis=1)
    data.loc[:,'bbox_string'] = data.bbox.apply(lambda val: ";".join([str(v) for v in val]))

    data.overlay_intensity_C = data.overlay_intensity_C.fillna(0)
    data.overlay_intensity_M = data.overlay_intensity_M.fillna(0)
    data.overlay_intensity_Y = data.overlay_intensity_Y.fillna(0)
    data.overlay_intensity_K = data.overlay_intensity_K.fillna(0.7)

    data.use_blow_up_region = data.use_blow_up_region.fillna(False)
    data.use_contract_region = data.use_contract_region.fillna(False)
    data.use_wave_deform = data.use_wave_deform.fillna(False)

    # results laden
    results = get_results_of_project(2)
    results = pd.DataFrame.from_dict(results)
    results.loc[:,'bbox_string'] = results.value.apply(lambda val: f'{ val["x"] };{ val["y"] };{ val["width"] };{ val["height"] }')
    results['img_name'] = results.img_name.str.replace('\.4c_\d+\.jpg$','.4c.jpg', regex=True)

    merged = pd.merge(
        data,
        results.loc[
            :,
            ['img_name','bbox_string','id']
        ],
        how="left",
        on=['img_name','bbox_string']
    )

    merged.loc[
        pd.isna(merged.id),
        'id'
    ] = merged.loc[pd.isna(merged.id)].apply(lambda row: get_temp_id(), axis=1)

    return merged


def main():
    dotenv = load_dotenv()
    con = sqlite3.connect(dotenv['DB_PATH'])

    data = load_data_to_process( dotenv )

    # Dateien schreiben
    write_generic_images( data, con )
    write_masks( data, con )
    write_adjustments_per_mask( data, con )


if __name__ == '__main__':
    main()