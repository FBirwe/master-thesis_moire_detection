import shutil
from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from file_interaction import copy_blob, get_blobs, blob_exists


def move_files():
    dotenv = load_dotenv()
    source_blobs = get_blobs( filter='generic_data/' )
    target_blobs = get_blobs( filter='labelstudio_generic_data/' )
    screen_4c_files = [blob for blob in source_blobs if blob.endswith(f'.4c_{ dotenv["LOFI_DPI"] }.jpg')]
    blobs_to_copy = []

    for img_path in tqdm( screen_4c_files ):
        out_path = f'labelstudio_generic_data/{ img_path.split("/")[-1] }'

        if out_path not in target_blobs:
            blobs_to_copy.append((
                img_path,
                out_path
            ))

    for source_path,out_path in tqdm(blobs_to_copy):
        copy_blob(
            source_path,
            out_path
        )


if __name__ == '__main__':
    move_files()