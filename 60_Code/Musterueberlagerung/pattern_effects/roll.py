import numpy as np
from PIL import Image


def roll_image( img, pattern_stretch_factor=1 ):
    img = np.array(img)
    A = img.shape[0] / 2.0
    w = 2.0 / img.shape[1]
    
    shift = lambda x: A * np.sin(2.0*np.pi*x * w * (1/pattern_stretch_factor))
    
    img_out = np.zeros(img.shape)
    for i in range(img.shape[0]):
        img_out[:,i] = np.roll(img[:,i], int(shift(i)))

    return Image.fromarray(img_out.astype('uint8'))