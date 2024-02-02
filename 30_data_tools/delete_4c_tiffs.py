from helper import load_dotenv
from tqdm import tqdm


def main():
    dotenv = load_dotenv()
    tiff_data = list(dotenv['DATA_DIR'].glob('./*/*/*.4c.tiff'))

    print( "remaining 4c tiffs", len(tiff_data) )
    for i in tqdm(range(min([1000,len(tiff_data)]))):
        tiff_data[i].unlink()



if __name__ == '__main__':
    main()