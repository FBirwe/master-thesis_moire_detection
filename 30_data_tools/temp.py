import shutil
from helper import load_dotenv
from tqdm import tqdm

config = load_dotenv()

def sort_masks():
    pkls = [
        pkl for pkl in config['DATA_DIR'].glob('./**/*.pkl')
        if pkl.parent.name == 'halftone300dpiMasks'    
    ]

    for pkl in tqdm( pkls ):
        mask_dir = pkl.parent.parent / 'halftone300dpi'

        if mask_dir.exists() == False:
            mask_dir.mkdir()

        out_path = mask_dir / pkl.name

        shutil.move(
            pkl,
            out_path
        )

def rename_files():
    # jpgs
    jpgs = [
        jpg for jpg in config['DATA_DIR'].glob('./*/halftone300dpi/*.jpg')
        if jpg.name.strip(jpg.suffix).endswith('.4c') != True
    ]

    for jpg in tqdm(jpgs):
        out_path = jpg.parent / (jpg.name.strip( jpg.suffix ) + ".4c" + jpg.suffix)
        jpg.rename( out_path )

    # masks
    masks = [
        m for m in config['DATA_DIR'].glob('./*/halftone300dpi/*.pkl')
        if m.name.strip(m.suffix).endswith('.masks') != True
    ]

    for m in tqdm(masks):
        out_path = m.parent / (m.name.strip( m.suffix ) + ".masks" + m.suffix)
        m.rename( out_path )


rename_files()