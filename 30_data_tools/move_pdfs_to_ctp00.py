from helper import move_all_files
from dotenv import dotenv_values
from pathlib import Path

def main():
    config = dict(dotenv_values(".env"))
    config['DATA_DIR'] = Path( config['DATA_DIR'] )
    sort_dir = config['DATA_DIR'] / config['SORT_DIR'] / 'pdf'
    to_dir = Path('/Volumes/ctp_00/Jobs/Frederic_MA_Tests/UserDefinedFolders/Eingangsdaten/Testdata')

    move_all_files(
        sort_dir,
        to_dir,
        extensions=['.pdf']
    )


main()