import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import json


def get_feature_importance_df( masks, adjustments_per_mask ):

    # basis regression data
    regression_data = masks.loc[
        :,
        ['mask_id' ,'overlay_intensity_K', 'K_mean_coverage', 'K_std_coverage', 'pattern_shape', 'pattern_coverage', 'cover_style', 'ssim', 'label']
    ].copy()
    regression_data.pattern_coverage.fillna(0, inplace=True)

    pattern_shape_encoder = LabelEncoder()
    pattern_shape_encoder.fit(regression_data.pattern_shape)
    regression_data.pattern_shape = pattern_shape_encoder.transform(regression_data.pattern_shape)

    cover_style_encoder = LabelEncoder()
    cover_style_encoder.fit(regression_data.cover_style)
    regression_data.cover_style = cover_style_encoder.transform(regression_data.cover_style)

    # Effects
    # Scale
    regression_data = pd.merge(
        regression_data,
        get_scale_data( adjustments_per_mask ),
        on='mask_id',
        how="left"
    )

    # Rotation
    regression_data = pd.merge(
        regression_data,
        get_rotation_data( adjustments_per_mask ),
        on='mask_id',
        how="left"
    )
    regression_data.rotation_degree.fillna(0,inplace=True)

    # Blow Up Centered
    regression_data = pd.merge(
        regression_data,
        get_blow_centered_data( adjustments_per_mask ),
        on='mask_id',
        how="left"
    )
    regression_data.centered_c_blow_up.fillna(0,inplace=True)

    # Contract Centered
    regression_data = pd.merge(
        regression_data,
        get_contract_centered_data( adjustments_per_mask ),
        on='mask_id',
        how="left"
    )
    regression_data.centered_c_contract.fillna(0,inplace=True)

    # Distortion
    distortion_data = get_distortion_data( adjustments_per_mask )
    regression_data = pd.merge(
        regression_data,
        distortion_data,
        on='mask_id',
        how="left"
    )

    for c in distortion_data.columns:
        if c != 'mask_id':
            regression_data[c].fillna(0,inplace=True)


    # BlowUp Region
    blow_up_region_data = get_blow_up_region_data( adjustments_per_mask )
    regression_data = pd.merge(
        regression_data,
        blow_up_region_data,
        on='mask_id',
        how="left"
    )

    for c in blow_up_region_data.columns:
        if c != 'mask_id':
            regression_data[c].fillna(0,inplace=True)

    # Contract Region
    contract_region_data = get_contract_region_data( adjustments_per_mask )
    regression_data = pd.merge(
        regression_data,
        contract_region_data,
        on='mask_id',
        how="left"
    )

    for c in contract_region_data.columns:
        if c != 'mask_id':
            regression_data[c].fillna(0,inplace=True)

    # Wave Deform
    wave_deform_data = get_wave_deform_data( adjustments_per_mask )
    regression_data = pd.merge(
        regression_data,
        wave_deform_data,
        on='mask_id',
        how="left"
    )

    for c in contract_region_data.columns:
        if c != 'mask_id':
            regression_data[c].fillna(0,inplace=True)





    # filter for NaN
    for c in regression_data.columns:
        regression_data = regression_data.loc[
            pd.isna(regression_data[c]) == False
        ]

    return regression_data


def get_scale_data( adjustments_per_mask ):
    stretch_data = pd.DataFrame.from_dict(
        [json.loads(val) for val in adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'stretch'].features]
    )
    stretch_data.loc[:,'mask_id'] = adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'stretch'].mask_id.to_numpy()

    scale_data = pd.merge(
        adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'scale'].mask_id,
        adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'scale'].features.apply( lambda val: json.loads(val)['scale'] ),
        left_index=True,
        right_index=True
    ).rename(columns={'features':'scale'})
    scale_data.scale.fillna(1, inplace=True)
    scale_data.loc[:,'stretch_x'] = scale_data.scale
    scale_data.loc[:,'stretch_y'] = scale_data.scale

    scale_data = pd.concat([
        stretch_data,
        scale_data
    ], ignore_index=True)

    return scale_data.loc[:,['mask_id','stretch_x','stretch_y']]


def get_rotation_data( adjustments_per_mask ):
    return pd.merge(
        adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'rotation'].mask_id,
        adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'rotation'].features.apply( lambda val: json.loads(val)['rotation_degree'] ),
        left_index=True,
        right_index=True
    ).rename(columns={'features':'rotation_degree'})


def get_blow_centered_data( adjustments_per_mask ):
    return pd.merge(
        adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'blow_up_centered'].mask_id,
        adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'blow_up_centered'].features.apply( lambda val: json.loads(val)['centered_c'] ),
        left_index=True,
        right_index=True
    ).rename(columns={'features':'centered_c_blow_up'})


def get_contract_centered_data( adjustments_per_mask ):
    return pd.merge(
        adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'contract_centered'].mask_id,
        adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'contract_centered'].features.apply( lambda val: json.loads(val)['centered_c'] ),
        left_index=True,
        right_index=True
    ).rename(columns={'features':'centered_c_contract'})


def get_corner_adjustments_for_uniform_distortion( row ):
    if row.trapezoidal_distortion_direction == 'top':
        corner_adjustments = [
            (row.trapezoidal_distortion_strength,0),
            (0,0),
            (0,0),
            (row.trapezoidal_distortion_strength,0)
        ]
    elif row.trapezoidal_distortion_direction == 'left':
        corner_adjustments = [
            (row.trapezoidal_distortion_strength,0),
            (row.trapezoidal_distortion_strength,0),
            (0,0),
            (0,0)
        ]
    elif row.trapezoidal_distortion_direction == 'bottom':
        corner_adjustments = [
            (0,0),
            (row.trapezoidal_distortion_strength,0),
            (row.trapezoidal_distortion_strength,0),
            (0,0)
        ]
    else:
        corner_adjustments = [
            (0,0),
            (0,0),
            (row.trapezoidal_distortion_strength,0),
            (row.trapezoidal_distortion_strength,0)
        ]

    return corner_adjustments


def get_distortion_data( adjustments_per_mask ):
    # normal distortion
    distortion_data = pd.DataFrame.from_dict([
        json.loads(val)
        for val in adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'trapezoidal_distortion'].features
    ])
    distortion_data.loc[
        :,
        'mask_id'
    ] = adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'trapezoidal_distortion'].mask_id.to_numpy()

    # uniform distortion
    uniform_distortion = pd.DataFrame.from_dict([
        json.loads(val)
        for val in adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'uniform_trapezoidal_distortion'].features
    ])
    uniform_distortion.loc[
        :,
        'mask_id'
    ] = adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'uniform_trapezoidal_distortion'].mask_id.to_numpy()
    uniform_distortion.loc[:,'corner_adjustments'] = uniform_distortion.apply( get_corner_adjustments_for_uniform_distortion, axis=1 )
    
    # zusammenführen
    distortion_data = pd.concat(
        [
            distortion_data,
            uniform_distortion
        ],
        ignore_index=True
    )
    
    distortion_data.loc[:,'top_left_x'] = distortion_data.corner_adjustments.apply(lambda val: val[0][0])
    distortion_data.loc[:,'top_left_y'] = distortion_data.corner_adjustments.apply(lambda val: val[0][1])
    distortion_data.loc[:,'bottom_left_x'] = distortion_data.corner_adjustments.apply(lambda val: val[1][0])
    distortion_data.loc[:,'bottom_left_y'] = distortion_data.corner_adjustments.apply(lambda val: val[1][1])
    distortion_data.loc[:,'bottom_right_x'] = distortion_data.corner_adjustments.apply(lambda val: val[2][0])
    distortion_data.loc[:,'bottom_right_y'] = distortion_data.corner_adjustments.apply(lambda val: val[2][1])
    distortion_data.loc[:,'top_right_x'] = distortion_data.corner_adjustments.apply(lambda val: val[3][0])
    distortion_data.loc[:,'top_right_y'] = distortion_data.corner_adjustments.apply(lambda val: val[3][1])
    
    return distortion_data.loc[
        :,
        ['mask_id','top_left_x','top_left_y','bottom_left_x','bottom_left_y','bottom_right_x','bottom_right_y','top_right_x','top_right_y']
    ]    


def get_blow_up_region_data( adjustments_per_mask ):
    blow_up_region_data = []

    for entry in adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'blow_up_region'].features:
        features = json.loads(entry)
        row = {
            'blow_up_count' : features['blow_up_count']
        }

        for i in range(int(features['blow_up_count'])):
            row[f'blow_up_radius_{(i+1)}'] = features['blow_up_radius'][i]
            row[f'blow_up_center_x_{(i+1)}'] = features['blow_up_center'][i][0]
            row[f'blow_up_center_y_{(i+1)}'] = features['blow_up_center'][i][1]
            row[f'blow_up_c_{(i+1)}'] = features['blow_up_c'][i]

        blow_up_region_data.append(row)

    blow_up_region_data = pd.DataFrame.from_dict(blow_up_region_data)
    blow_up_region_data.loc[:,'mask_id'] = adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'blow_up_region'].mask_id.to_numpy()
    
    return blow_up_region_data


def get_contract_region_data( adjustments_per_mask ):
    contract_region_data = []

    for entry in adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'contract_region'].features:
        features = json.loads(entry)
        row = {
            'contract_count' : features['contract_count']
        }

        for i in range(int(features['contract_count'])):
            row[f'contract_radius_{(i+1)}'] = features['contract_radius'][i]
            row[f'contract_center_x_{(i+1)}'] = features['contract_center'][i][0]
            row[f'contract_center_y_{(i+1)}'] = features['contract_center'][i][1]
            row[f'contract_c_{(i+1)}'] = features['contract_c'][i]

        contract_region_data.append(row)

    contract_region_data = pd.DataFrame.from_dict(contract_region_data)
    contract_region_data.loc[:,'mask_id'] = adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'contract_region'].mask_id.to_numpy()
    
    return contract_region_data


def get_wave_deform_data( adjustments_per_mask ):
    wave_deform_data = []

    for entry in adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'wave_deform'].features:
        features = json.loads(entry)
        row = {}

        if 'wave_overlay_count' in features:
            row['wave_overlay_count'] = features['wave_overlay_count']
    
            for i in range(len(features['wave_configurations'])):
                wave_length, wave_depth = features['wave_configurations'][i]
                row[f'wave_length_{(i+1)}'] = wave_length
                row[f'wave_depth_{(i+1)}'] = wave_depth
        else:
            row['wave_overlay_count'] = 1
            row['wave_length_1'] =  features['wave_length']
            row['wave_depth_1'] =  features['wave_depth']
        
        wave_deform_data.append(row)

    wave_deform_data = pd.DataFrame.from_dict(wave_deform_data)
    wave_deform_data.loc[:,'mask_id'] = adjustments_per_mask.loc[adjustments_per_mask.adjustment == 'wave_deform'].mask_id.to_numpy()

    for c in wave_deform_data.columns:
        if c != 'mask_id':
            wave_deform_data[c].fillna(0, inplace=True)
    
    return wave_deform_data