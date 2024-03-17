import sys
sys.path.append('../../30_data_tools/')

from pathlib import Path
import json
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
    dotenv = load_dotenv()

    pattern_path = dotenv['PATTERN_DIR'] / f'{ pattern_name }.tif'
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
    random_val = abs(np.random.normal(0, config['effect_selection_sigma'], None))
    if random_val > 1:
        random_val = 1

    if random_val <= len(adjustments_to_use) / len([key for key in config['adjustments'] if config['adjustments'][key]['weight'] > 0]):
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


def get_pattern_style(config, mask):
    Image.MAX_IMAGE_PIXELS = None

    row = {}
    adjustments_to_use = get_adjustments_to_use([], config)
    row['pattern'] = random.choice(config['available_patterns'])
    row['effect_order'] = adjustments_to_use
    row['effects'] = []
    shuffle( row['effect_order'] )

    # Die Position des Bildes auf der Maske wird zufällig ausgewählt
    pattern_img_size = get_pattern_img(row['pattern'], config).size

    row['pattern_img_position'] = (
        random.randrange(
            min(mask['bbox'][2] - pattern_img_size[0], 0),
            max(mask['bbox'][2] - pattern_img_size[0], 0)
        ) if mask['bbox'][2] - pattern_img_size[0] != 0 else 0,
        random.randrange(
            min(mask['bbox'][3] - pattern_img_size[1], 0),
            max(mask['bbox'][3] - pattern_img_size[1], 0)
        ) if mask['bbox'][3] - pattern_img_size[1] else 0
    )

    # Die Effekte werden in die JSON eingebaut
    for effect_name in row['effect_order']:
        effect = {
            'effect_name' : effect_name
        }

        if effect_name == 'blow_up_centered':
            effect['centered_c'] = config['adjustments']['blow_up_centered']['c']

        if effect_name == 'blow_up_region':
            min_count = config['adjustments']['blow_up_region']['min_count']
            max_count = config['adjustments']['blow_up_region']['max_count']
            effect['blow_up_count'] = int(random.randrange(min_count, max_count))
            effect['blow_up_radius'] = []
            effect['blow_up_center'] = []
            effect['blow_up_c'] = []

            for i in range(int(effect['blow_up_count'])):
                img_size = get_pattern_img( row["pattern"], config ).size
                radius = random.randrange(
                    config['adjustments']['blow_up_region']['min_radius'],
                    config['adjustments']['blow_up_region']['max_radius']    
                )
                effect['blow_up_radius'].append( radius )
                effect['blow_up_center'].append((
                    random.randrange(radius, img_size[0] - radius),
                    random.randrange(radius, img_size[1] - radius)
                ))
                effect['blow_up_c'].append(config['adjustments']['blow_up_region']['c'])

        if effect_name == 'contract_centered':
            effect['centered_c'] = config['adjustments']['blow_up_centered']['c']

        if effect_name == 'contract_region':
            min_count = config['adjustments']['contract_region']['min_count']
            max_count = config['adjustments']['contract_region']['max_count']
            effect['contract_count'] = int(random.randrange(min_count, max_count))
            effect['contract_radius'] = []
            effect['contract_center'] = []
            effect['contract_c'] = []

            for i in range(int(effect['contract_count'])):
                img_size = get_pattern_img( row["pattern"], config ).size
                radius = random.randrange(
                    config['adjustments']['contract_region']['min_radius'],
                    config['adjustments']['contract_region']['max_radius']    
                )
                effect['contract_radius'].append( radius )
                effect['contract_center'].append((
                    random.randrange(radius, img_size[0] - radius),
                    random.randrange(radius, img_size[1] - radius)
                ))
                effect['contract_c'].append(config['adjustments']['contract_region']['c'])

        # Drehung
        if effect_name == 'rotation':
            # Der Rotationswinkel wird auf einen zufälligen Wert zwischen -x und +x gesetzt
            # mit x als Wert für "degree_span"
            degree_span = config['adjustments']['rotation']['degree_span']
            base_degree = config['adjustments']['rotation']['base_degree']

            if degree_span == 0:
                effect['rotation_degree'] = base_degree
            else:
                effect['rotation_degree'] = base_degree + random.randrange(degree_span * 2) - degree_span
        
        # Skalierung
        if effect_name == 'scale':
            effect['scale'] = config['adjustments']['scale']['max_size']

        if effect_name == 'stretch':
            effect['stretch_x'] = random.random() * (
                config['adjustments']['stretch']['max_stretch_x'] - 
                config['adjustments']['stretch']['min_stretch_x']
            ) + config['adjustments']['stretch']['min_stretch_x']
            effect['stretch_y'] = random.random() * (
                config['adjustments']['stretch']['max_stretch_y'] - 
                config['adjustments']['stretch']['min_stretch_y']
            ) + config['adjustments']['stretch']['min_stretch_y']


        if effect_name == 'trapezoidal_distortion':
            effect['trapezoidal_distortion_strength_1'] = random.random() * (
                config['adjustments']['trapezoidal_distortion']['max_strength_1'] - 
                config['adjustments']['trapezoidal_distortion']['min_strength_1']
            ) + config['adjustments']['trapezoidal_distortion']['min_strength_1']
            effect['trapezoidal_distortion_strength_2'] = random.random() * (
                config['adjustments']['trapezoidal_distortion']['max_strength_2'] - 
                config['adjustments']['trapezoidal_distortion']['min_strength_2']
            ) + config['adjustments']['trapezoidal_distortion']['min_strength_2']
            effect['trapezoidal_distortion_direction'] = random.choices(
                ['left','right','top','bottom'],
                weights=config['adjustments']['trapezoidal_distortion']['chance_directions'],
                k=1
            )[0]

        if effect_name == 'uniform_trapezoidal_distortion':
            effect['trapezoidal_distortion_strength'] = random.random() * (
                config['adjustments']['uniform_trapezoidal_distortion']['max_strength'] - 
                config['adjustments']['uniform_trapezoidal_distortion']['min_strength']
            ) + config['adjustments']['uniform_trapezoidal_distortion']['min_strength']

            effect['trapezoidal_distortion_direction'] = random.choices(
                ['left','right','top','bottom'],
                weights=config['adjustments']['trapezoidal_distortion']['chance_directions'],
                k=1
            )[0]    
        
        if effect_name == 'wave_deform':
            effect['wave_length'] = random.randrange(
                config['adjustments']['wave_deform']['min_wave_length'],
                config['adjustments']['wave_deform']['max_wave_length']
            )
            effect['wave_depth'] = random.randrange(
                config['adjustments']['wave_deform']['min_wave_depth'],
                config['adjustments']['wave_deform']['max_wave_depth']
            )
        
        # Kissenverzerrung
        if effect_name == 'pillow_disortion':
            effect['pillow_depth_x'] = random.random() - 0.5
            effect['pillow_depth_y'] = random.random() - 0.5

        row['effects'].append(effect)

    return row


def get_pattern_img_by_style( row, config ):
    pattern_img = get_pattern_img( row["pattern"], config )
    original_pattern_img_size = pattern_img.size

    for effect in row['effects']:
        # Effekte anwenden
        if effect['effect_name'] == 'blow_up_centered':
            pattern_img = blow_up( pattern_img, effect['centered_c'] )

        if effect['effect_name'] == 'blow_up_region':
            for i in range(int(effect['blow_up_count'])):
                radius = effect['blow_up_radius'][i]
                center = effect['blow_up_center'][i]
                c = effect['blow_up_c'][i]
                
                pattern_img = blow_up_region( pattern_img, radius, center, c )

        if effect['effect_name'] == 'contract_region':
            for i in range(int(effect['contract_count'])):
                radius = effect['contract_radius'][i]
                center = effect['contract_center'][i]
                c = effect['contract_c'][i]
                
                pattern_img = contract_region( pattern_img, radius, center, c )

        if effect['effect_name'] == 'contract_centered':
            pattern_img = contract( pattern_img, effect['centered_c'] )

        if effect['effect_name'] == 'pillow_disortion':
            pattern_img = pillow_deform( pattern_img, effect['pillow_depth_x'], effect['pillow_depth_y'] )
            
        if effect['effect_name'] == 'roll':
            pattern_img = roll_image(
                pattern_img,
                pattern_stretch_factor=config['adjustments']['roll']['pattern_stretch_factor']
            )

        if effect['effect_name'] == 'rotation':
            pattern_img = pattern_img.rotate( effect['rotation_degree'], expand=1, fillcolor="black" )

        if effect['effect_name'] == 'scale':
            pattern_img = pattern_img.resize((
                int(pattern_img.size[0] * effect['scale']),
                int(pattern_img.size[1] * effect['scale'])
            ))

        if effect['effect_name'] == 'stretch':
            pattern_img = stretch( pattern_img, effect['stretch_x'], effect['stretch_y'] )

        if effect['effect_name'] == 'trapezoidal_distortion':
            pattern_img = distort_trapezoidal(
                pattern_img,
                (
                    effect['trapezoidal_distortion_strength_1'],
                    effect['trapezoidal_distortion_strength_2']
                ),
                effect['trapezoidal_distortion_direction']
            )

        if effect['effect_name'] == 'uniform_trapezoidal_distortion':
            pattern_img = distort_trapezoidal_uniform(
                pattern_img,
                effect['trapezoidal_distortion_strength'],
                effect['trapezoidal_distortion_direction']
            )

        if effect['effect_name'] == 'wave_deform':
            pattern_img = wave_deform(
                pattern_img,
                effect['wave_length'],
                effect['wave_depth']
            )
    
    # Originalgröße wieder einrichten
    if original_pattern_img_size[0] < pattern_img.size[0]:
        margin = round((pattern_img.size[0] - original_pattern_img_size[0]) * 0.5)

        pattern_img = pattern_img.crop((
            margin,0,
            margin + original_pattern_img_size[0],pattern_img.size[1]
        ))

    if original_pattern_img_size[1] < pattern_img.size[1]:
        margin = round((pattern_img.size[1] - original_pattern_img_size[1]) * 0.5)

        pattern_img = pattern_img.crop((
            0,margin,
            pattern_img.size[0],margin + original_pattern_img_size[1]
        ))


    return pattern_img