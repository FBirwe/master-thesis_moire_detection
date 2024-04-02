import re
from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv, get_pdf_page_processing_status
from file_interaction import get_related_filepath, download_blob, upload_buffer
from add_data_to_db import add_related_file
from PIL import Image
import numpy as np
import re
from random import shuffle
from io import BytesIO


SEPARATIONS = ['C','M','Y','K']


def generate_4c_images( data_to_update ):
    Image.MAX_IMAGE_PIXELS = None
    dotenv = load_dotenv()
    target_dpi = dotenv["LOFI_DPI"]
    variant_name = 'ps2400dpi150lpi'
    type_name = f'4c_{ target_dpi }'

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
    dotenv = load_dotenv()
    target_dpi = dotenv["LOFI_DPI"]
    variant_name = 'ps2400dpi150lpi'
    type_name = f'4c_{ target_dpi }'

    data = get_pdf_page_processing_status( variant_name, type_name )
    data_to_update = data.loc[data.file_available == False]
    # data_to_update = data_to_update.iloc[:10]
    # print( data_to_update.filename )

    generate_4c_images( data_to_update )