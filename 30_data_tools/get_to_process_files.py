from pathlib import Path
from dotenv import dotenv_values
from tqdm import tqdm
import shutil
import sqlite3

def get_relevant_pdf_file( sort_file, pdf_files ):
    relevant_pdf_files = [
        pdf for pdf in pdf_files
        if pdf.name.replace(pdf.suffix,'') in sort_file.name
    ]

    if len(relevant_pdf_files) == 0:
        return None

    if len(relevant_pdf_files) == 1:
        return relevant_pdf_files[0]

    # kommen mehrere Kandidaten in Frage,
    # wird diejenige Datei mit der längsten
    # Übereinstimmung zum Zuge.
    # Da der VPS-Name immer gleich ist,
    # kann die Länge des Dateinamens stattdessen
    # herangezogen werden.
    return sorted(
        pdf_files,
        key=lambda pdf: len(pdf.name),
        reverse=True
    )[0]

def get_target_job( sort_file, pdf_files ):
    job_dir = get_relevant_pdf_file( sort_file, pdf_files ).parent.parent

    return job_dir


def sort( input_dir, data_dir ):
    files_to_sort = list( input_dir.glob('./*/*.VPS') )
    available_pdf = list( data_dir.glob('./**/*.pdf') )

    for f in tqdm(files_to_sort):
        job_dir = get_target_job( f, available_pdf )

        # Ziel-Dir anlegen
        target_dir = job_dir / f.parent.name
        if target_dir.exists() == False:
            target_dir.mkdir()

        # Datei verschieben
        target_file = target_dir / f.name.replace(f.suffix,'.tiff')
        shutil.move(
            f,
            target_file
        )


def main():
    config = dict(dotenv_values(".env"))
    config['DATA_DIR'] = Path(config['DATA_DIR'])
    config['SORT_DIR'] = config['DATA_DIR'] / config['SORT_DIR']

    sort( config['SORT_DIR'], config['DATA_DIR'] )

main()