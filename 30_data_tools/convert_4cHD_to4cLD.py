from PIL import Image
Image.MAX_IMAGE_PIXELS = 2351589062
from helper import load_dotenv,get_relevant_data_dirs
from pathlib import Path
import re
from tqdm import tqdm

def main():
    config = load_dotenv()
    target_dpi = config['LOFI_DPI']
    data_dirs = get_relevant_data_dirs()
    cmyk_files = []
    
    for ddir in data_dirs:
        cmyk_files += list( ddir.glob('./**/*4c.tiff') )
        cmyk_files += list( ddir.glob('./**/*4c.tif') )

    files_to_process = []

    for cmyk_file in cmyk_files:
        target_file_name = re.sub(
            r'4c$',
            f'4c_{ target_dpi }',
            cmyk_file.name.replace(cmyk_file.suffix,'')
        ) + '.jpg'
        target_file = cmyk_file.parent / target_file_name

        # wenn die Datei vorhanden ist, nicht überschreiben
        if target_file.exists() == False:
            files_to_process.append( (cmyk_file, target_file) )
    

    for cmyk_file, target_file in tqdm(files_to_process):
        print( target_file )
        img = Image.open( cmyk_file )
        img = img.resize(
            (
                int(round(img.size[0] / 2400 * target_dpi)),
                int(round(img.size[1] / 2400 * target_dpi))
            ),
            resample=Image.Resampling.BICUBIC
        )
        # img = img.convert(mode="RGB")
        
        img.save(
            target_file,
            'JPEG'
        )
        img.close()


if __name__ == '__main__':
    main()