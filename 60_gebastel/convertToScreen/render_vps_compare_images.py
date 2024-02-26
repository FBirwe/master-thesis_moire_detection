from tqdm import tqdm
import sys
sys.path.append('../../30_data_tools')
from helper import load_dotenv
from render_screen_images import generate_screen
from random import shuffle


def get_images_to_process( config ):
    halftone_images = list(config['DATA_DIR'].glob('./*/halftone600dpi/*.4c.jpg'))

    images_to_process = []
    for img_path in halftone_images:

        separations_exist = [
            (img_path.parent.parent / 'ps2400dpi150lpi' / img_path.name.replace( '.4c.jpg', f'.{ sep }.tif' )).exists()
            for sep in ['C','M','Y','K']
        ]

        if False in separations_exist:
            images_to_process.append( img_path )

    shuffle(images_to_process)
    return images_to_process


def main():
    config = load_dotenv()

    for img_path in tqdm(get_images_to_process( config )):
        out_dir = img_path.parent.parent / 'ps2400dpi150lpi'

        if out_dir.exists() == False:
            out_dir.mkdir()

        cyan_path = out_dir / img_path.name.replace( '.4c' + img_path.suffix, '.C.tif' )
        magenta_path = out_dir / img_path.name.replace( '.4c' + img_path.suffix, '.M.tif' )
        yellow_path = out_dir / img_path.name.replace( '.4c' + img_path.suffix, '.Y.tif' )
        black_path = out_dir / img_path.name.replace( '.4c' + img_path.suffix, '.K.tif' )

        generate_screen(
            img_path.resolve(),
            cyan_path.resolve(),
            magenta_path.resolve(),
            yellow_path.resolve(),
            black_path.resolve()
        )

 
if __name__ == "__main__":
    main()