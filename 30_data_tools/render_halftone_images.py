import subprocess
from helper import load_dotenv, get_pdf_page_processing_status
from file_interaction import get_related_filepath, upload_file, download_blob
from add_data_to_db import add_related_file
from tqdm import tqdm
from pathlib import Path


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
    variant_name = f'halftone{ config["LOFI_DPI"] }dpi'
    data = get_pdf_page_processing_status( variant_name, '4c' )
    data_to_update = data.loc[data.file_available == False]
    temp_files = []

    for i in tqdm(range(data_to_update.shape[0])):
        row = data_to_update.iloc[i]
        pdf_path, storage_type = get_related_filepath( row.job, 'pdf', f'{row.filename}.pdf' )

        if storage_type == 'local':
            pdf_path = Path( pdf_path )
        else:
            temp_pdf_path = config['TEMP_PROCESSING_DIR'] / f'{ row.filename }.pdf'
            with temp_pdf_path.open('wb') as f:
                f.write(download_blob( pdf_path ).getbuffer())

            temp_files.append(temp_pdf_path)
            pdf_path = temp_pdf_path
        
        jpg_path = config['TEMP_PROCESSING_DIR'] / f'{ row.filename }.4c.jpg'
        temp_files.append(jpg_path)
        jpg_blob_path = f'data/{ row.job }/{ variant_name }/'
        
        render_halftone_image(
            pdf_path.resolve(),
            jpg_path.resolve()
        )

        # upload nach azure
        upload_file( jpg_path, jpg_blob_path )

        # Datei in DB einfügen
        add_related_file( row.job, row.filename, variant_name, '4c', jpg_path.name )

    # temp Ordner aufräumen
    for f in temp_files:
        f.unlink()