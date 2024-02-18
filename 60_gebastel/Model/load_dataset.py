import sys
sys.path.append('../../30_data_tools/')

from PIL import Image
import numpy as np
import pandas as pd
from tqdm import tqdm
from helper import load_dotenv
from get_labelstudio_data import get_results_of_project

def get_moire_path( row, dotenv ):
    return dotenv['GENERIC_GENERATED_DATA_DIR'] / (row.basic_name.replace('$PLACEHOLDER$', row.method) + f'.4c_{ dotenv["LOFI_DPI"] }.jpg')


def get_non_moire_path( row, dotenv ):
    return dotenv['DATA_DIR'] / row.job / 'ps2400dpi150lpi'/ (row.pdf_filename + '.4c_300.jpg')

    # non_moire_path = row.img_path.parent.parent / 'vps2400dpi150lpi'/ (row.image + '_300.jpg')

    # if non_moire_path.exists() == False:
    #     non_moire_path = row.img_path.parent.parent / 'vps2400dpi175lpi'/ (row.image + '_300.jpg')

    # return non_moire_path


def get_img_pair( row, img_size, dotenv ):

    non_moire_path = get_non_moire_path( row, dotenv )    
    moire_path = get_moire_path( row, dotenv )    
    
    non_moire_img = Image.open( non_moire_path )
    moire_img = Image.open( moire_path )
    rescale_factor = (
        non_moire_img.size[0] / moire_img.size[0],
        non_moire_img.size[1] / moire_img.size[1]
    )
    moire_img = moire_img.resize(non_moire_img.size)

    bbox = [
        int(round(row.bbox[0] * rescale_factor[0])),
        int(round(row.bbox[1] * rescale_factor[1])),
        int(round(row.bbox[2] * rescale_factor[0])),
        int(round(row.bbox[3] * rescale_factor[1]))
    ]
    
    cropped_non_moire_img = non_moire_img.crop((
        bbox[0],
        bbox[1],
        bbox[0] + bbox[2],
        bbox[1] + bbox[3]
    )).resize(img_size)
    cropped_moire_img = moire_img.crop((
        bbox[0],
        bbox[1],
        bbox[0] + bbox[2],
        bbox[1] + bbox[3]
    )).resize(img_size)

    cropped_non_moire_img = 1 - np.array(cropped_non_moire_img)[:,:,3] / 255
    cropped_moire_img = 1 - np.array(cropped_moire_img)[:,:,3] / 255
    
    return cropped_non_moire_img, cropped_moire_img


def get_available_moires():
    dotenv = load_dotenv()
    moire_results = [r for r in get_results_of_project(2) if 'checked_moire' in r['rectanglelabels']]

    results_frame = pd.DataFrame(
        [
            (
                r['img_name'],
                "_".join([
                    str(r['value']['x']),
                    str(r['value']['y']),
                    str(r['value']['width']),
                    str(r['value']['height'])
                ]),
                r['rectanglelabels'][0]
            )
            for r in moire_results
        ],
        columns=['img_name','bbox_str','label']
    )

    data = pd.concat([pd.read_pickle(pkl) for pkl in dotenv['GENERIC_INFORMATION_DATA_DIR'].glob('./*.pkl')])
    data.loc[
        :,
        'img_name'
    ] = data.apply( lambda row: row.basic_name.replace( '$PLACEHOLDER$', row.method ) + f'.4c_{ dotenv["LOFI_DPI"] }.jpg', axis=1 )
    data.loc[
        :,
        'bbox_str'
    ] = data.bbox.apply( lambda bbox: "_".join([str(val) for val in bbox]) )

    merged = pd.merge(
        data,
        results_frame,
        how="left",
        on=['img_name','bbox_str']
    )

    merged = merged.loc[
        merged.label == 'checked_moire'
    ]

    return merged


def get_train_data( df, img_size ):
    dotenv = load_dotenv()
    data = []
    labels = []

    #for i in tqdm(range(100)):
    for i in tqdm(range(df.shape[0])):
        row = df.iloc[i]
        try:
            non_moire_img, moire_img = get_img_pair( row, img_size, dotenv )

            data.append(non_moire_img)
            data.append(moire_img)
        
            labels.append(0)
            labels.append(1)
        except:
            pass

    data = np.array(data)
    data = np.array([np.array([data[i,:,:],data[i,:,:],data[i,:,:]]) for i in range(data.shape[0])])
    labels = np.array(labels)

    return data, labels