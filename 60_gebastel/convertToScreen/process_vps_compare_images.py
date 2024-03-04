import re
from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv, get_pdf_page_processing_status
from file_interaction import get_data_files, get_related_filepath, download_blob, upload_buffer
from add_data_to_db import add_related_file
from PIL import Image
import numpy as np
import re
from random import shuffle
from io import BytesIO


SEPARATIONS = ['C','M','Y','K']


def load_separation_images_to_process( variant_name, dotenv ):
    all_files = get_data_files()

    sep_images = [
        img for img in all_files
        if str(img[0]).spit('/')[-2] == variant_name 
    ]

    target_dpi = dotenv['LOFI_DPI']
    images_by_separation = {}

    for sep_img in sep_images:
        sep_name = str(sep_img[0]).split('/')[-1]
        base_name, sep = re.match(r'(.+)\.(.+)\..+?$', sep_name).groups()
        
        halftone_img_path = sep_img.parent / f'{ base_name }.4c_{ target_dpi }.jpg'

        if sep in SEPARATIONS and halftone_img_path.exists() == False:
            
            if base_name not in images_by_separation:
                images_by_separation[base_name] = {}

            images_by_separation[base_name][sep] = sep_img

    return images_by_separation


def generate_4c_images():
    Image.MAX_IMAGE_PIXELS = None
    dotenv = load_dotenv()
    target_dpi = dotenv["LOFI_DPI"]
    variant_name = 'ps2400dpi150lpi'
    type_name = f'4c_{ target_dpi }'

    data = get_pdf_page_processing_status( variant_name, type_name )
    data_to_update = data.loc[data.file_available == False]

    for i in tqdm(range(data_to_update.shape[0])):
        row = data_to_update.iloc[i]

        out_filename = f'{ row.filename }.{ type_name }.jpg'
        out_path = f'data/{ row.job }/{ variant_name }/{ out_filename }'
        target_size = None 
        cmyk_img = None
        
        for i in range(len(SEPARATIONS)):
            c = SEPARATIONS[i]

            # print( row.job, variant_name, f'{ row.filename }.{ c }.tiff' )
            res = get_related_filepath(
                row.job,
                variant_name,
                f'{ row.filename }.{ c }.tif'
            )

            if res:
                separation_img_path, storage_type = res

                if storage_type == 'azure':
                    img = Image.open( download_blob( separation_img_path ) )
                else:
                    img = Image.open( separation_img_path )

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
            imagefile = BytesIO()
            Image.fromarray(255 - cmyk_img, mode="CMYK").save( imagefile, format='JPEG', dpi=(target_dpi, target_dpi), progressive=True )

            # buffer hochladen
            upload_buffer(
                imagefile.getvalue(),
                out_path
            )

            # related file hinzufügen
            add_related_file( row.job, row.filename, variant_name, type_name, out_filename )


if __name__ == '__main__':
    generate_4c_images()