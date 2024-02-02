from dotenv import dotenv_values
from pathlib import Path
import shutil
import re
from tqdm import tqdm
import sqlite3


def get_unprocessed_files_of_job( job_dir, target ):
    pdfs = list( (job_dir / 'pdf').glob('./*.pdf') )
    
    target_dir = job_dir / target
    
    if target_dir.exists() == False:
        return pdfs
    
    tiffs = list( target_dir.glob('./*.tiff') )
    
    pdfs_out = []
    
    def check_pdf( pdf ):
        pdf_regex = re.compile(f'{ pdf.name.replace(pdf.suffix,"") }.+?\.tiff$')
        
        for tiff in tiffs:
            if pdf_regex.match( tiff.name ):
                return True
        
        return False

    
    for pdf in pdfs:
        if check_pdf(pdf) == False:
            pdfs_out.append(pdf)

    return pdfs_out


def get_file_by_extension( dir_path, filename, extensions ):
    for ext in extensions:
        out_file = dir_path / f'{ filename }.{ ext }'

        if out_file.exists():
            return out_file
        
    return None


def get_pdf_pages( con ):
    c = con.cursor()

    c.execute('''SELECT * FROM pdf_page pp''')
    rows = c.fetchall()
    c.close()

    return [
        { 'filename' : r[0], 'job' : r[1], 'screen_ruling' : r[2] }
        for r in rows
    ]


def has_vps_file( pdf_name, target, con ):
    c = con.cursor()
    c.execute(f'''
                SELECT * FROM related_file rf 
                WHERE pdf_filename = "{ pdf_name }"
                AND "type" IN ("C","M","Y","K")
                AND variant_name = "{ target }"
    ''')
    res = c.fetchone()
     
    return res is not None


def main():
    config = dict(dotenv_values(".env"))
    config['DATA_DIR'] = Path( config['DATA_DIR'] )
    con = sqlite3.connect( config['DB_PATH'] )

    pdf_pages = get_pdf_pages(con)
    pdf_sort_dir = config['DATA_DIR'] / config['SORT_DIR'] / 'pdf'
    if pdf_sort_dir.exists() == False:
        pdf_sort_dir.mkdir()


    for job_name in tqdm(set([p['job'] for p in pdf_pages])):
        relevant_pdfs = [p for p in pdf_pages if p['job'] == job_name]
        job_dir = config['DATA_DIR'] / job_name

        for pdf in relevant_pdfs:
            needs_processing = has_vps_file( pdf['filename'], f'vps2400dpi{pdf["screen_ruling"]}lpi', con ) == False
            
            if needs_processing:
                orig_file = get_file_by_extension( job_dir / 'pdf', pdf['filename'], ['pdf','PDF'] )
                out_file = pdf_sort_dir / f"{pdf['job']}_{pdf['filename']}_{ pdf['screen_ruling'] }.pdf"

                shutil.copy( orig_file, out_file )


main()