import sys
sys.path.append('../../30_data_tools/')
from helper import load_dotenv
from get_labelstudio_data import get_results_of_project
import pandas as pd
import sqlite3

def get_images_with_scores():
    dotenv = load_dotenv()
    con = sqlite3.connect(dotenv['DB_PATH'])

    # images laden
    images = pd.read_sql(
        '''
            SELECT cf.*, mf.mask_filename FROM (
            	SELECT * FROM related_file
            	WHERE variant_name = 'halftone600dpi' AND "type" = '4c'
            ) cf
            LEFT JOIN (
            	SELECT job, pdf_filename, filename AS mask_filename, 1 AS has_mask FROM related_file 
            	WHERE variant_name = 'halftone600dpi' AND "type" = 'masks'
            ) mf ON cf.job=mf.job AND cf.pdf_filename=mf.pdf_filename 
            WHERE mf.has_mask IS NOT NULL
        ''',
        con
    )

    # masken laden
    masks = pd.read_sql(
        '''
            SELECT m.*, gi."timestamp" FROM mask m 
            LEFT JOIN generic_image gi 
            ON 
            	m.pdf_filename = gi.pdf_filename AND 
            	m.job = gi.job AND 
            	m."type" = gi."type" AND 
            	m.variant_name = gi.variant_name AND 
            	m."method" = gi."method" AND 
            	m.idx = gi.idx 
        ''',
        con,
        parse_dates=['timestamp']
    )
    results = get_results_of_project(2)

    masks = pd.merge(
        masks,
        pd.DataFrame(
            [(r['id'], r['rectanglelabels'][0]) for r in results if 'id' in r],
            columns=['mask_id','label']
        ),
        how="left",
        on="mask_id"
    )

    # Gruppieren
    grouped = masks.loc[
        :,
        ['job','pdf_filename','idx']
    ].groupby(['job','pdf_filename']).count()
    
    grouped['no_moire'] = masks.loc[
        masks.label == 'checked_no_moire',
        ['job','pdf_filename','idx']
    ].groupby(['job','pdf_filename']).count().idx
    
    grouped['moire'] = masks.loc[
        masks.label == 'checked_moire',
        ['job','pdf_filename','idx']
    ].groupby(['job','pdf_filename']).count().idx
    
    grouped = grouped.fillna(0)
    
    grouped.rename(columns={'idx':'total'}, inplace=True)
    grouped.loc[
        :,
        'score'
    ] = 0 - grouped.no_moire + grouped.moire
    
    grouped = grouped.reset_index()
    
    # score jobbasiert anpassen
    grouped_by_job = grouped.reset_index().loc[
        grouped.job.str.contains('randomPages') == False,
        ['job','score']
    ].groupby('job').mean()
    
    # grouped einpflegen
    images = pd.merge(
        images,
        grouped.loc[
            :,
            ['job','pdf_filename','score']
        ],
        how="left",
        on=['job','pdf_filename']
    )
    images.score = images.score.fillna(0)

    for job,row in grouped_by_job.iterrows():
        images.loc[
            images.job == job,
            'score'
        ] += row.score
    
    return images