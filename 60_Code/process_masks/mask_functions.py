import scipy
import numpy as np
import pytesseract
from pathlib import Path
from dotenv import dotenv_values
import sys
sys.path.append('../../30_data_tools/')
from helper import load_dotenv
from file_interaction import upload_buffer, download_blob
import cv2
import pickle


def get_config():
    config = dict(dotenv_values( Path(__file__).parent / ".env" ))
    config['MASK_MIN_AREA'] = int(config['MASK_MIN_AREA'])
    config['OCR_MIN_CONFIDENCE'] = int(config['OCR_MIN_CONFIDENCE'])
    config['MIN_MASK_OCR_INTERSECTION'] = float(config['MIN_MASK_OCR_INTERSECTION'])
    config['MIN_IOU'] = float(config['MIN_IOU'])
    config['MASK_IMG_SCALE_FACTOR'] = float(config['MASK_IMG_SCALE_FACTOR'])
    config['MASK_MAX_AREA_SHARE'] = float(config['MASK_MAX_AREA_SHARE'])

    return config


def get_whole_mask( m ):
    whole_mask = np.zeros((m['img_size'][1],m['img_size'][0]))
    # mask_img = scipy.signal.medfilt(
    #     m['mask'],
    #     kernel_size=[5,5]
    # )

    whole_mask[
        int(m['bbox'][1]):int(m['bbox'][1]) + m['mask'].shape[0],
        int(m['bbox'][0]):int(m['bbox'][0]) + m['mask'].shape[1]
    ] = m['mask']

    return whole_mask


def load_mask_img( m ):
    if abs(m['mask'].shape[1] - m['bbox'][2]) <= 1 or abs(m['mask'].shape[0] - m['bbox'][3]) <= 1:
        return m['mask']

    return cv2.resize(
        m['mask'].astype('uint8'), (m['bbox'][2],m['bbox'][3])
    ).astype('bool')


def load_masks( mask_path ):
    """
        Lädt Masken aus dem Pfad,
        skaliert diese und montiert sie
        in die Gesamtmaske ein
    """
    if mask_path is None:
        raise Exception('file not available')
    
    mask_path, storage_type = mask_path

    if storage_type == 'azure':
        masks = pickle.loads( download_blob(mask_path).getbuffer() )
    else:
        with mask_path.open('rb') as pkl_file:
            masks = pickle.load(pkl_file)

    for m in masks:
        m['bbox'] = [int(val) for val in m['bbox']]
        m['mask'] = load_mask_img( m )
        m['area'] = m['mask'].sum()
    
    return masks


def save_masks( masks, mask_path ):
    config = get_config()

    for m in masks:
        if m['mask'].shape[1] == m['bbox'][0] and m['mask'].shape[0] == m['bbox'][1]:
            m['mask'] = cv2.resize(
                m['mask'].astype('uint8'),
                (0,0),
                fx=config['MASK_IMG_SCALE_FACTOR'],
                fy=config['MASK_IMG_SCALE_FACTOR']
            ).astype('bool')

    upload_buffer(
        pickle.dumps(masks),
        mask_path
    )


def get_text_boxes( img, min_conf=50 ):
    """
        Erkennt Textboxen auf dem übergebenen Bild
        und gibt diese mit der erkannten Confidence zurück.
    """

    load_dotenv()
    res = pytesseract.image_to_data(
        img,
        output_type=pytesseract.Output.DICT
    )

    
    out = []
    for i in range(len(res['conf'])):
        if res['conf'][i] > min_conf and res['text'][i].strip() != '':
            row = {}

            for key in ['conf','left','top','width','height']:
                row[key] = res[key][i]

            row['right'] = row['left'] + row['width']
            row['bottom'] = row['top'] + row['height']
            
            out.append(row)

    return out


def is_text_mask( img, m, debug=False ):
    config = get_config()

    cropped_img = img.convert('RGB').crop((
        m['bbox'][0],
        m['bbox'][1],
        m['bbox'][0]+m['bbox'][2],
        m['bbox'][1]+m['bbox'][3]
    ))
    text_boxes = get_text_boxes(
        cropped_img,
        min_conf=config['OCR_MIN_CONFIDENCE']
    )

    if len(text_boxes) == 0:
        return False

    left = min([tb['left'] for tb in text_boxes])
    top = min([tb['top'] for tb in text_boxes])
    right = max([tb['right'] for tb in text_boxes])
    bottom = max([tb['bottom'] for tb in text_boxes])
    
    area_text = (right - left) * (bottom - top)
    area_img = cropped_img.size[0] * cropped_img.size[1]

    intersection = area_text / area_img

    if debug:
        print( intersection )
    
    return intersection >= config['MIN_MASK_OCR_INTERSECTION']


def get_iou( whole_mask_a, whole_mask_b ):
    """
        Errechnet die Intersection over union (IoU) für zwei Masken 
    """
    combined_map = whole_mask_a + whole_mask_b

    intersection = combined_map[combined_map >= 2].sum()
    union = combined_map[combined_map > 0].sum()

    return intersection / union


def calc_bbox_iou( bbox_a, bbox_b ):
    intersection_box = [
        max([bbox_a[0], bbox_b[0]]),
        max([bbox_a[1], bbox_b[1]]),
        min([bbox_a[0]+bbox_a[2], bbox_b[0]+bbox_b[2]]),
        min([bbox_a[1]+bbox_a[3], bbox_b[1]+bbox_b[3]])
    ]
    intersection = (intersection_box[0] - intersection_box[2]) * (intersection_box[1] - intersection_box[3])

    union_box = [
        min([bbox_a[0], bbox_b[0]]),
        min([bbox_a[1], bbox_b[1]]),
        max([bbox_a[0]+bbox_a[2], bbox_b[0]+bbox_b[2]]),
        max([bbox_a[1]+bbox_a[3], bbox_b[1]+bbox_b[3]])
    ]
    union = (union_box[0] - union_box[2]) * (union_box[1] - union_box[3])

    if intersection < 0:
        return 0
    
    return intersection / union


def filter_intersected_masks( masks ):
    config = get_config()
    delete = []
    whole_masks = {}

    for a in range(len(masks)):
        if a not in delete:
            for b in range(a+1, len(masks)):
                if b not in delete:
                    iou_bbox = calc_bbox_iou(
                        masks[a]['bbox'],
                        masks[b]['bbox']
                    )

                    if iou_bbox >= config['MIN_MASK_OCR_INTERSECTION']:
                        if a not in whole_masks:
                            whole_masks[a] = get_whole_mask(masks[a])

                        if b not in whole_masks:
                            whole_masks[b] = get_whole_mask(masks[a])
                    
                        iou = get_iou( whole_masks[a],  whole_masks[b] )
    
                        if iou >= config['MIN_MASK_OCR_INTERSECTION']:
                            delete.append(b)
    
    return [masks[i] for i in range(len(masks)) if i not in delete]


def is_above_min_size( m ):
    config = get_config()
    area = m['bbox'][2] * m['bbox'][3]
    
    return area >= config['MASK_MIN_AREA']


def is_below_max_size( m ):
    config = get_config()
    area = m['mask'].sum()
    
    return area < config['MASK_MAX_AREA_SHARE'] * m['img_size'][0] * m['img_size'][1]


if __name__ == '__main__':
    print(get_config())