import sys
sys.path.append('../../30_data_tools/')

from pathlib import Path
import random
from PIL import Image
from pattern_effects.blow_up import blow_up, contract, blow_up_region, contract_region
from pattern_effects.stretch import stretch
from pattern_effects.trapezoidal_distortion import distort_trapezoidal, distort_trapezoidal_uniform
from pattern_effects.roll import roll_image
from pattern_effects.pillow_deform import pillow_deform
from pattern_effects.wave_deform import wave_deform
from helper import load_dotenv
import numpy as np
from random import shuffle


def get_pattern_img( pattern_name, config ):
    Image.MAX_IMAGE_PIXELS = None

    pattern_path = load_dotenv()['PATTERN_DIR'] / f'{ pattern_name }.tif'
    pattern_img = Image.open(pattern_path)
    pattern_resize_factor = config['processing_dpi'] / 2400
    pattern_img = pattern_img.convert('L').resize(
        (
            int(pattern_img.size[0] * pattern_resize_factor),
            int(pattern_img.size[1] * pattern_resize_factor)
        ),
        resample=Image.BICUBIC
    )

    return pattern_img


def get_adjustments_to_use(adjustments_to_use, config):    
    excluded_adjustments = []
    for adjustment in adjustments_to_use:
        if "excludes" in config['adjustments'][adjustment]:
            excluded_adjustments += config['adjustments'][adjustment]['excludes']
    
    available_adjustments = [
        key for key in config['adjustments']
        if (
            config['adjustments'][key]['weight'] > 0 and
            key not in excluded_adjustments and
            key not in adjustments_to_use
        )
    ]

    # adjustments mit Weight=1 sollen immer enthalten sein
    adjustments_to_use += [
        key for key in available_adjustments
        if config['adjustments'][key]['weight'] == 1
    ]
            

    if len(available_adjustments) == 0:
        return adjustments_to_use

    # termination function
    # steuert, ob weitere Anpassungen verwendet werden sollen
    random_val = abs(np.random.normal(0, 0.8, 1)[0])
    if random_val > 1:
        random_val = 1

    if random_val < len(adjustments_to_use) / len(available_adjustments):
        return adjustments_to_use

    next_item = random.choices(
        available_adjustments,
        weights=[config['adjustments'][key]['weight'] for key in available_adjustments],
        k=1
    )[0]
    while next_item in adjustments_to_use:
        next_item = random.choices(
            available_adjustments,
            weights=[config['adjustments'][key]['weight'] for key in available_adjustments],
            k=1
        )[0]
        
    adjustments_to_use.append(next_item)
    
    return get_adjustments_to_use(adjustments_to_use, config)


def get_pattern_style(config):
    Image.MAX_IMAGE_PIXELS = None

    row = {
        'use_blow_up_centered' : False,
        'use_blow_up_region' : False,
        'use_contract_centered' : False,
        'use_contract_region' : False,
        'use_pillow_disortion' : False,
        'use_roll' : False,
        'use_rotation' : False,
        'use_scale' : False,
        'use_stretch' : False,
        'use_trapezoidal_distortion' : False,
        'use_uniform_trapezoidal_distortion' : False,
        'use_wave_deform' : False
    }
    adjustments_to_use = get_adjustments_to_use([], config)
    row['pattern'] = random.choice(config['available_patterns'])
    row['effect_order'] = adjustments_to_use
    shuffle( row['effect_order'] )

    if 'blow_up_centered' in adjustments_to_use:
        row['use_blow_up_centered'] = True
        row['centered_c'] = config['adjustments']['blow_up_centered']['c']

    if 'blow_up_region' in adjustments_to_use:
        row['use_blow_up_region'] = True

        min_count = config['adjustments']['blow_up_region']['min_count']
        max_count = config['adjustments']['blow_up_region']['max_count']
        row['blow_up_count'] = int(random.randrange(min_count, max_count))
        row['blow_up_radius'] = []
        row['blow_up_center'] = []
        row['blow_up_c'] = []

        for i in range(int(row['blow_up_count'])):
            img_size = get_pattern_img( row["pattern"], config ).size
            radius = random.randrange(
                config['adjustments']['blow_up_region']['min_radius'],
                config['adjustments']['blow_up_region']['max_radius']    
            )
            row['blow_up_radius'].append( radius )
            row['blow_up_center'].append((
                random.randrange(radius, img_size[0] - radius),
                random.randrange(radius, img_size[1] - radius)
            ))
            row['blow_up_c'].append(config['adjustments']['blow_up_region']['c'])

    if 'contract_centered' in adjustments_to_use:
        row['use_contract_centered'] = True
        row['centered_c'] = config['adjustments']['blow_up_centered']['c']
    

    if 'contract_region' in adjustments_to_use:
        row['use_contract_region'] = True

        min_count = config['adjustments']['contract_region']['min_count']
        max_count = config['adjustments']['contract_region']['max_count']
        row['contract_count'] = int(random.randrange(min_count, max_count))
        row['contract_radius'] = []
        row['contract_center'] = []
        row['contract_c'] = []

        for i in range(int(row['contract_count'])):
            img_size = get_pattern_img( row["pattern"], config ).size
            radius = random.randrange(
                config['adjustments']['contract_region']['min_radius'],
                config['adjustments']['contract_region']['max_radius']    
            )
            row['contract_radius'].append( radius )
            row['contract_center'].append((
                random.randrange(radius, img_size[0] - radius),
                random.randrange(radius, img_size[1] - radius)
            ))
            row['contract_c'].append(config['adjustments']['contract_region']['c'])


    # Roll
    if 'roll' in adjustments_to_use:
        row['use_roll'] = True

    # Drehung
    if 'rotation' in adjustments_to_use:
        # Der Rotationswinkel wird auf einen zufälligen Wert zwischen -x und +x gesetzt
        # mit x als Wert für "degree_span"
        row['use_rotation'] = True
        degree_span = config['adjustments']['rotation']['degree_span']
        base_degree = config['adjustments']['rotation']['base_degree']

        if degree_span == 0:
            row['rotation_degree'] = base_degree
        else:
            row['rotation_degree'] = base_degree + random.randrange(degree_span * 2) - degree_span
    
    # Skalierung
    if 'scale' in adjustments_to_use:
        row['use_scale'] = True
        row['scale'] = config['adjustments']['scale']['max_size']

    if 'stretch' in adjustments_to_use:
        row['use_stretch'] = True
        row['stretch_x'] = random.random() * (
            config['adjustments']['stretch']['max_stretch_x'] - 
            config['adjustments']['stretch']['min_stretch_x']
        ) + config['adjustments']['stretch']['min_stretch_x']
        row['stretch_y'] = random.random() * (
            config['adjustments']['stretch']['max_stretch_y'] - 
            config['adjustments']['stretch']['min_stretch_y']
        ) + config['adjustments']['stretch']['min_stretch_y']


    if 'trapezoidal_distortion' in adjustments_to_use:
        row['use_trapezoidal_distortion'] = True
        row['trapezoidal_distortion_strength_1'] = random.random() * (
            config['adjustments']['trapezoidal_distortion']['max_strength_1'] - 
            config['adjustments']['trapezoidal_distortion']['min_strength_1']
        ) + config['adjustments']['trapezoidal_distortion']['min_strength_1']
        row['trapezoidal_distortion_strength_2'] = random.random() * (
            config['adjustments']['trapezoidal_distortion']['max_strength_2'] - 
            config['adjustments']['trapezoidal_distortion']['min_strength_2']
        ) + config['adjustments']['trapezoidal_distortion']['min_strength_2']
        row['trapezoidal_distortion_direction'] = random.choices(
            ['left','right','top','bottom'],
            weights=config['adjustments']['trapezoidal_distortion']['chance_directions'],
            k=1
        )[0]

    if 'uniform_trapezoidal_distortion' in adjustments_to_use:
        row['use_uniform_trapezoidal_distortion'] = True
        row['trapezoidal_distortion_strength'] = random.random() * (
            config['adjustments']['uniform_trapezoidal_distortion']['max_strength'] - 
            config['adjustments']['uniform_trapezoidal_distortion']['min_strength']
        ) + config['adjustments']['uniform_trapezoidal_distortion']['min_strength']

        row['trapezoidal_distortion_direction'] = random.choices(
            ['left','right','top','bottom'],
            weights=config['adjustments']['trapezoidal_distortion']['chance_directions'],
            k=1
        )[0]    
    
    if 'wave_deform' in adjustments_to_use:
        row['use_wave_deform'] = True
        row['wave_length'] = random.randrange(
            config['adjustments']['wave_deform']['min_wave_length'],
            config['adjustments']['wave_deform']['max_wave_length']
        )
        row['wave_depth'] = random.randrange(
            config['adjustments']['wave_deform']['min_wave_depth'],
            config['adjustments']['wave_deform']['max_wave_depth']
        )
    
    # Kissenverzerrung
    if 'pillow_disortion' in adjustments_to_use:
        row['use_pillow_disortion']
        row['pillow_depth_x'] = random.random() - 0.5
        row['pillow_depth_y'] = random.random() - 0.5

    return row


def get_pattern_img_by_style( row, config ):
    pattern_img = get_pattern_img( row["pattern"], config )

    for effect in row['effect_order']:
        # Effekte anwenden
        if effect == 'blow_up_centered':
            pattern_img = blow_up( pattern_img, row['centered_c'] )

        if effect == 'blow_up_region':
            for i in range(int(row['blow_up_count'])):
                radius = row['blow_up_radius'][i]
                center = row['blow_up_center'][i]
                c = row['blow_up_c'][i]
                
                pattern_img = blow_up_region( pattern_img, radius, center, c )

        if effect == 'contract_region':
            for i in range(int(row['contract_count'])):
                radius = row['contract_radius'][i]
                center = row['contract_center'][i]
                c = row['contract_c'][i]
                
                pattern_img = contract_region( pattern_img, radius, center, c )

        if effect == 'contract_centered':
            pattern_img = contract( pattern_img, row['centered_c'] )

        if effect == 'pillow_disortion':
            pattern_img = pillow_deform( pattern_img, row['pillow_depth_x'], row['pillow_depth_y'] )
            
        if effect == 'roll':
            pattern_img = roll_image(
                pattern_img,
                pattern_stretch_factor=config['adjustments']['roll']['pattern_stretch_factor']
            )

        if effect == 'rotation':
            pattern_img = pattern_img.rotate( row['rotation_degree'], expand=1, fillcolor="black" )

        if effect == 'scale':
            pattern_img = pattern_img.resize((
                int(pattern_img.size[0] * row['scale']),
                int(pattern_img.size[1] * row['scale'])
            ))

        if effect == 'stretch':
            pattern_img = stretch( pattern_img, row['stretch_x'], row['stretch_y'] )

        if effect == 'trapezoidal_distortion':
            pattern_img = distort_trapezoidal(
                pattern_img,
                (
                    row['trapezoidal_distortion_strength_1'],
                    row['trapezoidal_distortion_strength_2']
                ),
                row['trapezoidal_distortion_direction']
            )

        if effect == 'uniform_trapezoidal_distortion':
            pattern_img = distort_trapezoidal_uniform(
                pattern_img,
                row['trapezoidal_distortion_strength'],
                row['trapezoidal_distortion_direction']
            )

        if effect == 'wave_deform':
            pattern_img = wave_deform(
                pattern_img,
                row['wave_length'],
                row['wave_depth']
            )
    
    return pattern_img