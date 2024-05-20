import sys
sys.path.append('../../30_data_tools')
import numpy as np
import math
from skimage.metrics import structural_similarity as ssim
from scipy.ndimage import gaussian_filter
from PIL import Image
from helper import load_dotenv
import pickle


"""
    Mit Hilfe der vorliegenden Funktionen werden erzeugte Klassifizierungskacheln
    im Nachgang darauf bewertet, ob eine Moiréstruktur ausreichender Intensität entstanden ist.
"""

def get_fft( input_img ):
    ft = np.fft.ifftshift(np.array(input_img))
    ft = np.fft.fft2(ft)
    ft = np.fft.fftshift(ft)
    
    return ft


def limit_frequencies( fft, inner_limit=None, outer_limit=None ):
    center = (fft.shape[1] / 2, fft.shape[0] / 2)
    for y in range(fft.shape[0]):
        for x in range(fft.shape[1]):
            r = math.sqrt( abs(center[0] - x) ** 2 + abs(center[1] - y) ** 2 )
            
            if outer_limit is not None and r > outer_limit:
                fft[y,x] = 1
    
            if inner_limit is not None and r < inner_limit:
                fft[y,x] = 1

    return fft


def get_frequency_gain( orig_img, synthetic_img, additional=.00001 ):
    fft_orig = get_fft( orig_img )
    fft_synthetic = get_fft( synthetic_img )

    res = np.log( (np.abs(fft_orig) ** 2 + additional) / (np.abs(fft_synthetic) ** 2 + additional) )
    res = limit_frequencies( res, outer_limit=70 )
    res = gaussian_filter(res, sigma=3)

    return res


def get_diff_img_frequency_gain( orig_img, synthetic_img ):
    diff_img = Image.fromarray(gaussian_filter(np.array(synthetic_img) - np.array(orig_img),sigma=3))
    fft = np.abs( limit_frequencies( get_fft(diff_img), inner_limit=5 ) )
    fft = gaussian_filter(fft, sigma=3)

    return fft


def load_tile_classifier():
    dotenv = load_dotenv()

    with (dotenv['MODEL_DIR'] / 'svm_tile_postprocessing.pkl').open('rb') as pkl_file:
        clf = pickle.load( pkl_file )

    return clf


def get_tile_properties( moire_tile_path ):
    dotenv = load_dotenv()

    non_moire_tile_path = moire_tile_path.parent.parent / 'no_moire' / moire_tile_path.name
    moire_tile = Image.open( moire_tile_path ).convert('L')
    non_moire_tile = Image.open( non_moire_tile_path ).convert('L')
    frequency_gain = get_frequency_gain( moire_tile, non_moire_tile ).max()
    ssim_value = ssim( np.array(moire_tile), np.array(non_moire_tile) )

    return frequency_gain, ssim_value


def classify_tile( moire_tile_path, clf ):
    X = np.array([get_tile_properties( moire_tile_path )])

    return ['moire','no_moire'][clf.predict(X)[0]]


if __name__ == '__main__':
    dotenv = load_dotenv()
    example_tile = dotenv['TILE_DATASET_DIR'] / 'train' / 'moire' / '__DgcOXDEJ_150.0272.jpg'
    classifier = load_tile_classifier()

    print( classify_tile(example_tile, classifier) )