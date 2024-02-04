import shutil
from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv

def move_files():
    config = load_dotenv()

    for img_path in tqdm( config['GENERIC_GENERATED_DATA_DIR'].glob('./*.4c_600.jpg') ):
        out_path = config['GENERIC_LABELSTUDIO_DATA_DIR'] / img_path.name

        if out_path.exists() == False:
            shutil.copy(
                img_path,
                out_path
            )

if __name__ == '__main__':
    move_files()