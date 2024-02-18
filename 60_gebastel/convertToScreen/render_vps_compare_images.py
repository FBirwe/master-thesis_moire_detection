from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from render_screen_images import generate_screen
from random import shuffle


def get_images_to_process( config ):
    halftone_images = list(config['DATA_DIR'].glob('./*/vps2400dpi150lpi/*.4c_300.jpg'))

    images_to_process = []
    for img in halftone_images:
        img_name = img.name.replace('.4c_300.jpg','')
        img_path = img.parent.parent / 'halftone600dpi' / f"{img_name}.4c.jpg"

        separations_exist = [
            (img.parent.parent / 'ps2400dpi150lpi' / img_path.name.replace( '.4c.jpg', f'.4c.{ sep }.tif' )).exists()
            for sep in ['C','M','Y','K']
        ]

        if img_path.exists() and False in separations_exist:
            images_to_process.append( img_path )

    shuffle(images_to_process)
    return images_to_process


def main():
    config = load_dotenv()

    for img_path in tqdm(get_images_to_process( config )):
        out_dir = img_path.parent.parent / 'ps2400dpi150lpi'

        if out_dir.exists() == False:
            out_dir.mkdir()

        cyan_path = out_dir / img_path.name.replace( img_path.suffix, '.C.tif' )
        magenta_path = out_dir / img_path.name.replace( img_path.suffix, '.M.tif' )
        yellow_path = out_dir / img_path.name.replace( img_path.suffix, '.Y.tif' )
        black_path = out_dir / img_path.name.replace( img_path.suffix, '.K.tif' )

        generate_screen(
            img_path.resolve(),
            cyan_path.resolve(),
            magenta_path.resolve(),
            yellow_path.resolve(),
            black_path.resolve()
        )

 
if __name__ == "__main__":
    main()