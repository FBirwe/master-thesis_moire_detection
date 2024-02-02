from pathlib import Path
from dotenv import dotenv_values
from tqdm import tqdm
import shutil
import sqlite3
import re

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


def get_target_job( sort_file, pdfs ):
    res = re.match(r'(.+)_\d{3}\.p1.+\.VPS', sort_file.name )

    if res:
        sort_file_base_name = res.groups()[0]
        matching_pdfs = [
            pdf for pdf in pdfs
            if pdf[0] == sort_file_base_name
        ]

        if len(matching_pdfs) > 0:
            return matching_pdfs[0][1]

    return None


def sort( input_dir, data_dir ):
    files_to_sort = list( input_dir.glob('./*/*.VPS') )
    errors = 0

    for f in tqdm(files_to_sort):
        try:
            res = re.match(r'(.+?)_(.+)', f.name.strip(f.suffix))

            if res:
                job = res.groups()[0]
                job_dir = data_dir / job

                # # Ziel-Dir anlegen
                target_dir = job_dir / f.parent.name
                if target_dir.exists() == False:
                    target_dir.mkdir()

                # Datei verschieben
                target_file = target_dir / f'{ res.groups()[1] }.tiff'
                shutil.move(
                    f,
                    target_file
                )
        except:
            errors += 1
        
    print( f'{ len(files_to_sort)-errors }/{ len(files_to_sort) } files successfully processed' )


def main():
    config = dict(dotenv_values(".env"))
    config['DATA_DIR'] = Path(config['DATA_DIR'])
    config['SORT_DIR'] = config['DATA_DIR'] / config['SORT_DIR']

    sort( config['SORT_DIR'], config['DATA_DIR'] )


if __name__ == '__main__':
    main()