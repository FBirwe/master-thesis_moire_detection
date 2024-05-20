import sys
from PIL import Image
from pathlib import Path
import json
import pickle
import numpy as np
import cv2
from pattern_creation import get_pattern_img_by_style
from apply_pattern import apply_pattern
from helper import load_dotenv

"""
    Erzeugt anhand der Jobs aus "muesterueberlagerung_get_samples.py" erstellten Vorgaben
    Seiten mit synthetischen Moirés.
"""

def load_data( data_dir ):
    with (data_dir / 'data.json').open() as json_file:
        data = json.load( json_file )

    img = Image.open( data_dir / f'{ data["rows"][0]["pdf_filename"] }.4c.jpg' )

    with ( data_dir / f'{ data["rows"][0]["pdf_filename"] }.masks.pkl' ).open('rb') as masks_file:
        masks = pickle.load( masks_file )

    return img, masks, data


def get_generic_image_name( job, pdf_filename, method, processing_dpi, next_idx ):
    return f"{ job }.{ pdf_filename }.halftone{ processing_dpi }dpi.{ method }.{ next_idx }.jpg"


def create_generic_image( data_dir ):
    img, masks, data = load_data( data_dir )
    out_img = np.array(img)
    dotenv = load_dotenv()


    for i in range(len(data['rows'])):
        m = masks[i]
        row = data['rows'][i]

        if data['rescale_factor'] != 1:
            m['mask'] = (cv2.resize(
                (m['mask'] * 255).astype('uint8'),
                (0,0),
                fx=data['rescale_factor'],
                fy=data['rescale_factor']
            ) / 255).round().astype('bool')
            m['bbox'] = [int(val * data['rescale_factor']) for val in m['bbox']]

        pattern_img = get_pattern_img_by_style(row, data['processing_dpi'] )
    
        ssim_value_C = 1
        ssim_value_M = 1
        ssim_value_Y = 1
        ssim_value_K = 1

        if row['overlay_intensity_C'] > 0:
            out_img[:,:,0],_, ssim_value_C = apply_pattern(
                out_img[:,:,0],
                pattern_img,
                m,
                row['pattern_img_position'],
                data,
                method=row['method'],
                overlay_weight=row['overlay_weight'] * data['overlay_intensity_C']
            )

        if row['overlay_intensity_M'] > 0:
            out_img[:,:,1],_, ssim_value_M = apply_pattern(
                out_img[:,:,1],
                pattern_img,
                m,
                row['pattern_img_position'],
                data,
                method=row['method'],
                overlay_weight=row['overlay_weight'] * row['overlay_intensity_M']
            )

        if row['overlay_intensity_Y'] > 0:
            out_img[:,:,2],_, ssim_value_Y = apply_pattern(
                out_img[:,:,2],
                pattern_img,
                m,
                row['pattern_img_position'],
                data,
                method=row['method'],
                overlay_weight=row['overlay_weight'] * row['overlay_intensity_Y']
            )

        if row['overlay_intensity_K'] > 0:
            out_img[:,:,3],_, ssim_value_K = apply_pattern(
                out_img[:,:,3],
                pattern_img,
                m,
                row['pattern_img_position'],
                data,
                method=row['method'],
                overlay_weight=row['overlay_weight'] * row['overlay_intensity_K']
            )
        
        row['ssim'] = (ssim_value_C + ssim_value_M + ssim_value_Y + ssim_value_K) / 4

    print("masks generated")
    print("data dir", data_dir)

    with (data_dir / 'data.json').open('w') as json_file:
        json.dump( data, json_file )

    print("json written")
    # bild ablegen
    #if len([r for r in data['rows'] if r['ssim'] > dotenv['MAX_TILE_SSIM']]) > 0: 
    generic_img_name = get_generic_image_name(
        data['rows'][0]['job'],
        data['rows'][0]['pdf_filename'],
        data['rows'][0]["method"],
        data['processing_dpi'],
        data['rows'][0]["idx"]
    )

    print("file_written")

    print( data_dir / generic_img_name )

    Image.fromarray(out_img,mode='CMYK').save(
        data_dir / "synthetic_moire.jpg",
        progressive=True,
        dpi=(data['processing_dpi'],data['processing_dpi'])
    )

if __name__ == '__main__':
    data_dir = Path( sys.argv[1] ) 

    create_generic_image( data_dir )