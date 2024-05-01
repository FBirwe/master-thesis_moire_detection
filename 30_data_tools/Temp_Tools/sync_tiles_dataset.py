import sys
sys.path.append('..')
from file_interaction import get_blobs, download_blob
from helper import load_dotenv
import pytz
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import zipfile
import shutil

def main():
    dataset_name = sys.argv[1]

    dotenv = load_dotenv()
    dataset_dir = dotenv['TILE_DATASET_DIR']
    relevant_blobs = get_blobs( filter=f'tile_datasets/{dataset_name}.zip' )

    if len(relevant_blobs) > 0:
        zip_blob = relevant_blobs[0]
        zip_path = dataset_dir / f'{dataset_name}.zip'
        target_directory = dataset_dir / dataset_name

        if target_directory.exists():
            shutil.rmtree( target_directory )

        target_directory.mkdir()
        print("directory cleaned")

        with zip_path.open('wb') as target_file:
            target_file.write( download_blob( zip_blob ).getvalue() )
        print("zipfile downloaded")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_directory)
        print("dataset extracted")

        # aufräumen
        if ( target_directory / '__MACOSX' ).exists():
            shutil.rmtree(( target_directory / '__MACOSX' ))

        zip_path.unlink()
        print("process finished")
    else:
        print("no such dataset")


if __name__ == '__main__':
    main()