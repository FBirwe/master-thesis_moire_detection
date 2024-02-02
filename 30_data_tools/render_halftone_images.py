import subprocess
from helper import load_dotenv
from tqdm import tqdm

def render_halftone_image( pdf_path, jpg_path ):
    res = subprocess.run(
        f'osascript ./convert_pdf.sctp "{ pdf_path }" "{ jpg_path }"',
        shell=True,
        capture_output=True
    )

def get_pdfs_to_update( config ):
    all_dirs = [entry for entry in config['DATA_DIR'].iterdir() if entry.is_dir() if entry not in [config['SORT_DIR'], config['LABEL_STUDIO_DIR']]]
    pdfs = []

    for dir_entry in all_dirs:
        current_pdfs = list( (dir_entry / 'pdf').glob('./*.pdf') )

        for pdf in current_pdfs:
            jpg_path = pdf.parent.parent / 'halftone600dpi' / pdf.name.replace('.pdf','.4c.jpg')

            if jpg_path.exists() == False:
                pdfs.append(pdf)

    return pdfs


if __name__ == "__main__":
    config = load_dotenv()
    pdfs_to_update = get_pdfs_to_update( config )
    # print( len(pdfs_to_update) )

    for i in range(len(pdfs_to_update)):
        pdf = pdfs_to_update[i]
        print( f'{(i+1)}/{len(pdfs_to_update)}', pdf.parent.parent.name, pdf.name )
        jpg_path = pdf.parent.parent / 'halftone600dpi' / pdf.name.replace('.pdf','.4c.jpg')
        
        if jpg_path.parent.exists() == False:
            jpg_path.parent.mkdir()

        render_halftone_image(
            pdf.resolve(),
            jpg_path.resolve()
        )