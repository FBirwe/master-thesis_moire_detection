from helper import load_dotenv, get_pdf_page_processing_status
import sqlite3
import shutil
from tqdm import tqdm
from file_interaction import get_related_filepath, copy_blob, get_blobs, upload_file


def main():
    dotenv = load_dotenv()
    target_dpi = dotenv["LOFI_DPI"]
    variant_name = 'ps2400dpi150lpi'
    type_name = f'4c_{ target_dpi }'

    related_files = get_pdf_page_processing_status( variant_name, type_name )
    related_files = related_files.loc[related_files.file_available == True]
    available_files = [
        af.replace('labelstudio_moire_data/','')
        for af in get_blobs( filter='labelstudio_moire_data/' )
    ]

    related_files = related_files.loc[
        related_files.apply( lambda val: f'{ val.job }.{ variant_name }.{ val.filename }.{ type_name }.jpg', axis=1 ).isin(available_files) == False
    ]


    for i in tqdm(range(related_files.shape[0])):
        row = related_files.iloc[i]

        res = get_related_filepath(
            row.job,
            variant_name,
            f'{ row.filename }.{ type_name }.jpg'
        )

        if res:
            target_path = f'labelstudio_moire_data/{ row.job }.{ variant_name }.{ row.filename }.{ type_name }.jpg'
            source_path, storage_type = res

            if storage_type == 'azure':
                copy_blob( source_path, target_path )
            else:
                upload_file( source_path, 'labelstudio_moire_data/', filename=f'{ row.job }.{ variant_name }.{ row.filename }.{ type_name }.jpg')
                

if __name__ == '__main__':
    main()