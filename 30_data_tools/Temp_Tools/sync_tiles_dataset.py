import sys
sys.path.append('..')
from file_interaction import get_blobs, download_blob
from helper import load_dotenv
import pytz
from pathlib import Path
from tqdm import tqdm
from datetime import datetime


def main():
    dotenv = load_dotenv()
    dataset_dir = dotenv['TILE_DATASET_DIR']
    relevant_blobs = get_blobs( filter='tile_datasets/', include_metadata=True )

    for blob in tqdm(relevant_blobs):
        target_path = dataset_dir / blob.name.replace( 'tile_datasets/', '' )
        
        # create directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.exists() == False:
            with target_path.open('wb') as target_file:
                target_file.write( download_blob( blob.name ).getvalue() )
        else:
            file_created = datetime.fromtimestamp(target_path.stat().st_ctime).astimezone( pytz.UTC )

            if file_created < blob['last_modified']:
                with target_path.open('wb') as target_file:
                   target_file.write( download_blob( blob.name ).getvalue() )

if __name__ == '__main__':
    main()