from pathlib import Path
import sys
import shutil
from tqdm import tqdm

def get_all_files( dir_path ):
    files = []

    for entry in dir_path.iterdir():
        if entry.is_dir():
            files += get_all_files( entry )
        else:
            files.append( entry )
    
    return files


if __name__ == '__main__':
    TARGET_DIR = Path( sys.argv[1] )

    # Dateien herauslesen
    files = []
    for entry in tqdm(list(TARGET_DIR.iterdir())):
        if entry.is_dir():
            files += get_all_files( entry )
    
    print(f"{ str(len(files)) } files to sort found")

    # Dateien verschieben
    for f in tqdm(files):
        out_path = TARGET_DIR / f.name

        shutil.move(
            f,
            out_path
        )
    
    print(f"{ str(len(files)) } files moved")