import re
from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from PIL import Image
from datetime import datetime
import pandas as pd
import numpy as np


SEPARATIONS = ['C','M','Y','K']


def load_data( pkl_path ):
    data = pd.read_pickle(pkl_path)
    data.loc[
        :,
        'timestamp'
    ] = datetime.fromtimestamp( int(pkl_path.name.strip(pkl_path.suffix)) )

    return data


def load_separation_images_to_process( config ):
    pkls = list(config['GENERIC_INFORMATION_DATA_DIR'].glob('./*.pkl'))
    data = pd.concat([load_data(pkl_path) for pkl_path in pkls])
    base_names = data.apply(lambda row: row.basic_name.replace('$PLACEHOLDER$',row.method), axis=1).unique()
    
    target_dpi = config['LOFI_DPI']
    images_by_separation = {}

    for base_name in base_names:
        separation = {}
        halftone_img_path = config['GENERIC_GENERATED_DATA_DIR'] / f'{ base_name }.4c_{ target_dpi }.jpg'
    
        if halftone_img_path.exists() == False:    
            for sep in SEPARATIONS:
                sep_path = config['GENERIC_GENERATED_DATA_DIR'] / f'{ base_name }.{ sep }.tif'
        
                if sep_path.exists():
                    separation[sep] = sep_path

            images_by_separation[base_name] = separation
    
    return images_by_separation


def generate_4c_images( config ):
    Image.MAX_IMAGE_PIXELS = None

    images_by_separation = load_separation_images_to_process( config )
    target_dpi = config['LOFI_DPI']

    for key in tqdm( images_by_separation ):
        try:
            out_path = config['GENERIC_GENERATED_DATA_DIR'] / f'{ key }.4c_{ target_dpi }.jpg'
            
            target_size = None 
            cmyk_img = None
            
            for i in range(len(SEPARATIONS)):
                c = SEPARATIONS[i]

                if c in images_by_separation[key]:
                    img = Image.open( images_by_separation[key][c] )

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
                Image.fromarray(255 - cmyk_img, mode="CMYK").save( out_path, dpi=(target_dpi, target_dpi), progressive=True )
        except Exception as e:
            print( key )
            print( e )


def main():
    config = load_dotenv()
    generate_4c_images( config )


if __name__ == '__main__':
    main()