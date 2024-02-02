from helper import move_all_files
from dotenv import dotenv_values
from pathlib import Path
import shutil
import re
from tqdm import tqdm

def main():
    config = dict(dotenv_values(".env"))
    config['DATA_DIR'] = Path( config['DATA_DIR'] )
    # sort_dir = config['DATA_DIR'] / config['SORT_DIR'] / 'vps2400dpi150lpi'
    from_dir = Path('/Volumes/ctp_00/Jobs/Frederic_MA_Tests/UserDefinedFolders/VPS-Pages')

    vps_files = list( from_dir.glob('./*.VPS') )

    for vps_file in tqdm(vps_files):
        res = re.match(r'(.+)_(\d+)\.p1\.(.+)$', vps_file.name.strip(vps_file.suffix))

        if res:
            base_name = res.groups()[0]
            lpi = res.groups()[1]
            sep = res.groups()[2]

            # target_dir
            target_dir = config['DATA_DIR'] / config['SORT_DIR'] / f'vps2400dpi{ lpi }lpi'

            if target_dir.exists() == False:
                target_dir.mkdir()

            target_file = target_dir / f'{ base_name }.{ sep }{ vps_file.suffix }'
            shutil.move(
                vps_file,
                target_file
            )

if __name__ == '__main__':
    main()