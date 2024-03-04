import sys
sys.path.append('../../30_data_tools/')
from pathlib import Path
from tqdm import tqdm
from segment_anything import SamAutomaticMaskGenerator, sam_model_registry
from PIL import Image
import numpy as np
import pandas as pd
import sqlite3
from time import time
from mask_functions import get_config, load_mask_img, is_below_max_size, is_above_min_size, is_text_mask, filter_intersected_masks, save_masks
from helper import load_dotenv, get_pdf_page_processing_status
from file_interaction import get_related_filepath, download_blob
from add_data_to_db import add_related_file
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import torch

def render_mask( row, mask_generator, config ):
    res = get_related_filepath(
        row.job,
        config['target_variant'],
        f'{ row.filename }.4c.jpg'
    )

    if res:
        filepath, storage_type = res

        if storage_type == 'azure':
            img = Image.open( download_blob( filepath ) )
        else:
            img = Image.open( filepath )

        orig_size = img.size
        img = img.resize((
            int( round(img.size[0] * config['MASK_IMG_SCALE_FACTOR']) ),
            int( round(img.size[1] * config['MASK_IMG_SCALE_FACTOR']) )
        ))
        
        masks = mask_generator.generate( np.array(img.convert("RGB")) )
        
        for m in masks:
            factor_x = orig_size[0] / m['segmentation'].shape[1]
            factor_y = orig_size[1] / m['segmentation'].shape[0]
            
            m['segmentation'] = m['segmentation'][
                int(m['bbox'][1]):int(m['bbox'][1]+m['bbox'][3]+1),
                int(m['bbox'][0]):int(m['bbox'][0]+m['bbox'][2]+1)
            ]
            m['bbox'] = [
                int(round(m['bbox'][0] * factor_x)),
                int(round(m['bbox'][1] * factor_y)),
                int(round(m['bbox'][2] * factor_x)),
                int(round(m['bbox'][3] * factor_y))
            ]
            m['point_coords'] = [[
                int(round(m['point_coords'][0][0] * factor_x)),
                int(round(m['point_coords'][0][1] * factor_y)),
            ]]

            m['crop_box'] = [
                int(round(m['crop_box'][0] * factor_x)),
                int(round(m['crop_box'][1] * factor_y)),
                int(round(m['crop_box'][2] * factor_x)),
                int(round(m['crop_box'][3] * factor_y))
            ]

        masks = [m for m in masks if m['area'] < (img.size[0] * img.size[1] * 0.25)]    
        masks_out = []

        for m in masks:
            mask_out = {
                'mask' : m['segmentation'],
                'bbox' : m['bbox'],
                'predicted_iou' : m['predicted_iou'],
                'stability_score' : m['stability_score'],
                'img_size' : orig_size
            }
            mask_out['mask'] = load_mask_img(mask_out)
            masks_out.append(mask_out)

        
        masks_out = [m for m in masks_out if is_below_max_size(m)]
        
        # filter by size
        masks_out = [m for m in masks_out if is_above_min_size(m)]

        # filter by text box
        masks_out = [m for m in masks_out if is_text_mask( img, m ) == False]

        # filter duplicates
        masks_out = filter_intersected_masks( masks_out )
        
        return masks_out


def main():
    dotenv = load_dotenv()
    config = get_config()
    config['target_variant'] = 'halftone600dpi'

    all_masks = get_pdf_page_processing_status( config['target_variant'], 'masks' )
    missing_masks = all_masks.loc[all_masks.file_available == False]

    sam = sam_model_registry["vit_h"](checkpoint=dotenv['MODEL_DIR'] / "sam_vit_h_4b8939.pth")
    
    if torch.cuda.is_available():
        sam.to(device=torch.cuda.device(0))
        print( torch.cuda.get_device_name(0) )

    mask_generator = SamAutomaticMaskGenerator(sam)

    for i in tqdm(range(missing_masks.shape[0])):
        row = missing_masks.iloc[i]

        masks = render_mask( row, mask_generator, config )

        if masks is not None:
            mask_path = f'data/{ row.job }/{ config["target_variant"] }/{ row.filename }.masks.pkl'

            save_masks( masks, mask_path )
            add_related_file( row.job, row.filename, config["target_variant"], 'masks', f'{ row.filename }.masks.pkl' )


if __name__ == '__main__':
    main()