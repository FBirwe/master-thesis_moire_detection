import re
from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from PIL import Image
import numpy as np
import re
from random import shuffle


SEPARATIONS = ['C','M','Y','K']


def load_separation_images_to_process( dotenv ):
    sep_images = list(dotenv['DATA_DIR'].glob('./*/ps2400dpi150lpi/*.tif'))
    target_dpi = dotenv['LOFI_DPI']
    images_by_separation = {}

    for sep_img in sep_images:
        base_name, sep = re.match(r'(.+)\.(.+)$', sep_img.name.replace(sep_img.suffix,'')).groups()
        
        halftone_img_path = sep_img.parent / f'{ base_name }.4c_{ target_dpi }.jpg'

        if sep in SEPARATIONS and halftone_img_path.exists() == False:
            
            if base_name not in images_by_separation:
                images_by_separation[base_name] = {}

            images_by_separation[base_name][sep] = sep_img

    return images_by_separation


def generate_4c_images( config ):
    Image.MAX_IMAGE_PIXELS = None

    images_by_separation = load_separation_images_to_process( config )
    target_dpi = config['LOFI_DPI']
    keys = list( images_by_separation.keys() )
    shuffle( keys )

    for key in tqdm( keys ):
        try:
            out_path = images_by_separation[key]['K'].parent / f'{ key }.4c_{ target_dpi }.jpg'
            
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
    dotenv = load_dotenv()
    generate_4c_images( dotenv )


if __name__ == '__main__':
    main()