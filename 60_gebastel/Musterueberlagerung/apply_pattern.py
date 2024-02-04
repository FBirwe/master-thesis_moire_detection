import sys
sys.path.append('../process_masks/')

import math
import numpy as np
from time import time
from PIL import ImageEnhance, ImageFilter, Image, ImageChops
from mask_functions import get_whole_mask
from skimage.metrics import structural_similarity as ssim


def apply_sigmoid( tile, sigmoid_stretch_factor=20 ):
    return 1 / (1 + math.e ** (-1 * ((tile - 0.5) * sigmoid_stretch_factor)))


def equal_tile_size( tile_a, tile_b ):    
    for i in range(len(tile_b.shape)):
        if tile_a.shape[i] < tile_b.shape[i]:
            tile_b = tile_b[
                0:tile_a.shape[0],
                0:tile_a.shape[1]
            ]
            break

    return tile_b


def change_brightness( img, strength ):
    y = (img - 0.5) ** 2
    y = y.max() - y
    
    if y.max() != 0:
        y /= y.max()
    y *= strength

    out_img = img * (1 + y)
    out_img[out_img > 1] = 1
    out_img[out_img < 0] = 0
    
    return out_img


def equal_brightness( source, target, difference_threshold=0.01, mask=None ):   
    out = source.copy()
    if mask:
        np_mask = equal_tile_size( target, np.array(mask) / 255 )    

    def get_diff():
        if mask:
            return abs((((out * np_mask).sum()+1) / (np_mask.sum()+1)) - (((target * np_mask).sum()+1) / (np_mask.sum()+1)))

        return abs(out.mean() - target.mean())
         
    diff = get_diff()
    i = 0
    
    while diff > difference_threshold and i < 3:  
        if out.max() != 0:
            strength = ((out.mean() - target.mean()) / out.mean()) * -1
            out = change_brightness( out, strength )
            out = (out - out.min())

            if out.max() != 0:
                out = out / out.max()
            
            diff = get_diff()

        i += 1

    
    out[out < 0] = 0
    out[out > 1] = 1
    return out


def apply_multiply( tile_a, tile_b, mask=None, adjust_brightness=True, difference_threshold=0.01 ):
    tile_a = tile_a / 255
    tile_b = tile_b / 255

    tile_b = equal_tile_size( tile_a, tile_b )   
    
    multiplied = 1 - (1 - tile_a) * (1 - tile_b)

    if adjust_brightness:
        multiplied = equal_brightness( multiplied, tile_a, mask=mask, difference_threshold=difference_threshold )
    
    return (multiplied * 255).astype('uint8')


def apply_screen( tile_a, tile_b, mask=None, difference_threshold=0.01 ):
    tile_a = tile_a / 255
    tile_b = tile_b / 255

    tile_b = equal_tile_size( tile_a, tile_b )
    
    #return ((2 * tile_b * ( 1 - tile_a ) + np.sqrt( tile_b ) * ( 2 * tile_a - 1 )) * 255).astype('uint8')
    screened = (tile_a * (1 - tile_b))
    screened = equal_brightness( screened, tile_a, mask=mask, difference_threshold=difference_threshold )
    
    return (screened * 255).astype('uint8')


def apply_soft_light( tile_a, tile_b, mask=None, difference_threshold=0.01, sigmoid_stretch_factor=20 ):
    tile_a = Image.fromarray(tile_a)
    tile_b = Image.fromarray(tile_b)

    soft_light = ImageChops.soft_light( tile_a, tile_b )

    out = equal_brightness( np.array(soft_light) / 255, np.array(tile_a) / 255, mask=mask, difference_threshold=difference_threshold )

    return (out * 255).astype('uint8')


    multiplied = apply_multiply( tile_a, tile_b, mask=mask, difference_threshold=difference_threshold )
    screened = apply_screen( tile_a, tile_b, mask=mask, difference_threshold=difference_threshold )

    #weights = tile_a / 255

    weights = apply_sigmoid( tile_a.astype('int32') / 255, sigmoid_stretch_factor=sigmoid_stretch_factor )
    out = ((multiplied * (weights)) + (screened * (1 - weights))).astype('uint8')
    
    return out


def get_tile_bounding_box( center, pattern_shape, img_shape ):
    start = [
        int(center[0] - pattern_shape[1] / 2),
        int(center[1] - pattern_shape[0] / 2)
    ]

    if start[0] < 0:
        start[0] = 0

    if start[1] < 0:
        start[1] = 0

    end = [
        int(center[0] + pattern_shape[1] / 2),
        int(center[1] + pattern_shape[0] / 2)
    ]

    if end[0] > img_shape[1]:
        end[0] = img_shape[1]

    if end[1] > img_shape[0]:
        end[1] = img_shape[0]

    return {
        'x1' : start[0],
        'y1' : start[1],
        'x2' : end[0],
        'y2' : end[1],
        'width' : end[0] - start[0],
        'height' : end[1] - start[1]
    }


def get_pattern_mask( pattern_img, thumb_sizes, mask_decrease_factor, per_size_blur_radius_factor, composite_blur_radius_factor, increase_contrast_factor ):
    pattern_mask = None

    for size in thumb_sizes:
        thumb = Image.fromarray(pattern_img).resize(
            (
                int(pattern_img.shape[1] / size),
                int(pattern_img.shape[0] / size)
            ),
             Image.BILINEAR
        )

        size_mask = np.array(thumb) != 0
        
        size_mask = Image.fromarray((size_mask * 255).astype('uint8')).resize(
            (int(pattern_img.shape[1] * mask_decrease_factor), int(pattern_img.shape[0] * mask_decrease_factor))
        ).filter(
            ImageFilter.GaussianBlur(radius=int(round(pattern_img.shape[1] * per_size_blur_radius_factor))) 
        )
        
        if pattern_mask is None:
            pattern_mask = np.zeros((int(pattern_img.shape[1] * mask_decrease_factor), int(pattern_img.shape[0] * mask_decrease_factor)))
        
        pattern_mask += size_mask

    pattern_mask = Image.fromarray(( pattern_mask / len(thumb_sizes) ).astype('uint8'))
    
    ## add margin
    left = round((pattern_img.shape[1] - pattern_mask.size[0]) / 2)
    top = round((pattern_img.shape[0] - pattern_mask.size[1]) / 2)
    out_image = Image.new(pattern_mask.mode, (int(pattern_img.shape[1]), int(pattern_img.shape[0])), 'black')
    out_image.paste(pattern_mask, (left, top))
    out_image = out_image.filter(
        ImageFilter.GaussianBlur(radius=int(round(pattern_img.shape[1] * composite_blur_radius_factor))) 
    )
    out_image = ImageEnhance.Contrast(out_image).enhance( increase_contrast_factor )

    return out_image


def apply_pattern( img, pattern_img, center, config, method='screen', overlay_weight=1, mask=None, log=lambda val: print(val) ):
    Image.MAX_IMAGE_PIXELS = None
    
    start = time()
    pattern_img = np.array(pattern_img)
    pattern_mask = get_pattern_mask(
        pattern_img,
        config['pattern_mask']['thumb_sizes'],
        config['pattern_mask']['mask_decrease_factor'],
        config['pattern_mask']['per_size_blur_radius_factor'],
        config['pattern_mask']['composite_blur_radius_factor'],
        config['pattern_mask']['increase_contrast_factor'],
    )

    # wenn eine maske vorhanden ist, wird das Pattern auf diese begrenzt
    if mask:
        start_left = int(pattern_img.shape[1] / 2 - mask['bbox'][2] / 2)
        start_top = int(pattern_img.shape[0] / 2 - mask['bbox'][3] / 2)

        pattern_mask = pattern_mask.crop((
            start_left,start_top,
            start_left+mask['bbox'][2],start_top+mask['bbox'][3]
        ))
        
        pattern_img = pattern_img[
            start_top:start_top+mask['bbox'][3],
            start_left:start_left+mask['bbox'][2]
        ]

    
    log(f'{ time() - start }: pattern mask berechnet')
    # maskenausschnitt berechnen
    bounding_box = get_tile_bounding_box(
        center,
        pattern_img.shape,
        img.shape
    )

    log(f'{ time() - start }: bounding box berechnet')

    img_tile = img[
        bounding_box['y1']:bounding_box['y2'],
        bounding_box['x1']:bounding_box['x2']
    ]

    if pattern_img.shape[0] > bounding_box['height']:
        start_top = int(round(pattern_img.shape[0] / 2 - bounding_box['height'] / 2))
        pattern_img = pattern_img[
            start_top:start_top + bounding_box['height'],
            :
        ]
        pattern_mask = pattern_mask.crop((
            0,
            start_top,
            pattern_mask.size[0],
            start_top + bounding_box['height']
        ))

    if pattern_img.shape[1] > bounding_box['width']:
        start_left = int(round(pattern_img.shape[1] / 2 - bounding_box['width'] / 2))
        pattern_img = pattern_img[
            :,
            start_left:start_left + bounding_box['width']
        ]
        pattern_mask = pattern_mask.crop((
            start_left,
            0,
            start_left + bounding_box['width'],
            pattern_mask.size[1]
        ))

    log(f'{ time() - start }: tiles berechnet')

    if method == 'screen':        
        new_tile = apply_screen(
            img_tile,
            pattern_img,
            mask=pattern_mask,
            difference_threshold=config['equal_brightness']['difference_threshold']
        )
    elif method == 'soft_light':
        new_tile = apply_soft_light(
            img_tile,
            pattern_img,
            mask=pattern_mask,
            difference_threshold=config['equal_brightness']['difference_threshold'],
            sigmoid_stretch_factor=config['soft_light']['sigmoid_stretch_factor']
        )
    else:
        new_tile = apply_multiply(
            img_tile,
            pattern_img,
            mask=pattern_mask,
            difference_threshold=config['equal_brightness']['difference_threshold']
        )

    log(f'{ time() - start }: Anwendung: { method } abgeschlossen')
    
    # Prüfung auf Ähnlichkeit
    ssim_value = ssim(
        img_tile,
        new_tile
    )

    log(f'{ time() - start }: ssim errechnet: { ssim_value }')

    out_img = img.copy()
    out_img[
        bounding_box['y1']:bounding_box['y2'],
        bounding_box['x1']:bounding_box['x2']
    ] = (out_img[
        bounding_box['y1']:bounding_box['y2'],
        bounding_box['x1']:bounding_box['x2']
    ] * (1 - overlay_weight) + new_tile * overlay_weight).round().astype('uint8')

    # pattern mask  
    pattern_mask = np.array(pattern_mask)[
        :bounding_box['height'],
        :bounding_box['width']
    ] / 255
    
    out_img[
        bounding_box['y1']:bounding_box['y2'],
        bounding_box['x1']:bounding_box['x2']
    ] = (out_img[
        bounding_box['y1']:bounding_box['y2'],
        bounding_box['x1']:bounding_box['x2']
    ]) * pattern_mask + (img[
        bounding_box['y1']:bounding_box['y2'],
        bounding_box['x1']:bounding_box['x2']
    ]) * (1 - pattern_mask)
    out_img = out_img.round().astype('uint8')


    # Weißbereiche
    out_img[img < 5] = img[img < 5]
    out_img[img > 250] = img[img > 250]

    log(f'{ time() - start }: tile eingepast')
    #return out_img, pattern_mask
    # element mask anwenden
    if mask:
        whole_mask = get_whole_mask(
            mask
        )
        out_img[whole_mask == False] = img[whole_mask == False]

    log(f'{ time() - start }: objektmaske angewendet')
    
    return out_img, pattern_mask, ssim_value