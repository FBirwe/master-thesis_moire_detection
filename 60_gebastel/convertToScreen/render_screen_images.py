import subprocess
from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from datetime import datetime
import pandas as pd


def load_data( pkl_path ):
    data = pd.read_pickle(pkl_path)
    data.loc[
        :,
        'timestamp'
    ] = datetime.fromtimestamp( int(pkl_path.name.strip(pkl_path.suffix)) )

    return data


def generate_screen( halftone_path, cyan_path, magenta_path, yellow_path, black_path ):
    res = subprocess.run(
        f'osascript ./generate_screen.sctp "{ halftone_path }" "{ cyan_path }" "{ magenta_path }" "{ yellow_path }" "{ black_path }"',
        shell=True,
        capture_output=True
    )

def get_images_to_process( config ):
    pkls = list(config['GENERIC_INFORMATION_DATA_DIR'].glob('./*.pkl'))
    data = pd.concat([load_data(pkl_path) for pkl_path in pkls])
    halftone_images = data.apply(lambda row: row.basic_name.replace('$PLACEHOLDER$',row.method) + ".jpg", axis=1).unique()

    images_to_process = []
    for img_name in halftone_images:
        img_path = config['GENERIC_GENERATED_DATA_DIR'] / img_name
        cyan_path = img_path.parent / img_path.name.replace( img_path.suffix, '.C.tif' )

        if img_path.exists() and cyan_path.exists() == False:
            images_to_process.append( img_path )

    return images_to_process


def main():
    config = load_dotenv()


    for img_path in tqdm(get_images_to_process( config )):
        cyan_path = img_path.parent / img_path.name.replace( img_path.suffix, '.C.tif' )
        magenta_path = img_path.parent / img_path.name.replace( img_path.suffix, '.M.tif' )
        yellow_path = img_path.parent / img_path.name.replace( img_path.suffix, '.Y.tif' )
        black_path = img_path.parent / img_path.name.replace( img_path.suffix, '.K.tif' )

        generate_screen(
            img_path.resolve(),
            cyan_path.resolve(),
            magenta_path.resolve(),
            yellow_path.resolve(),
            black_path.resolve()
        )

 
if __name__ == "__main__":
    main()