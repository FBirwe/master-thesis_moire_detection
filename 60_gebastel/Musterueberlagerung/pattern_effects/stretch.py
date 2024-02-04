from PIL import Image
import numpy as np
import cv2


def stretch( img, percentage_x, percentage_y ):
    orig_size = img.size
    img = (np.array(img) * 255).astype('uint8')
    
    out_img = cv2.resize(
        img,
        (0,0),
        fx=percentage_x,
        fy=percentage_y
    )

    return Image.fromarray(out_img).crop(
        (0,0, orig_size[0], orig_size[1])
    )