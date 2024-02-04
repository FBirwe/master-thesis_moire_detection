from PIL import ImageOps, Image
import cv2
import numpy as np

class TrapezoidalDistortionDeformer:
    def __init__(self, strength, direction ) -> None:
        # strength 1 => Verschieben der rechten Kante um 50% der Bildhöhe
        self.strength = strength
        self.direction = direction


    def getmesh(self, img):
        strength_top = self.strength * 0.5
        strength_bottom = 1 - self.strength * 0.5

        return [(
            # target rectangle
            (0, 0, img.size[0], img.size[1]),
            # corresponding source quadrilateral
            (0, 0, 0, img.size[1], img.size[0], int(img.size[1] * strength_bottom), img.size[0], int(img.size[1] * strength_top))
        )]
    

def distort_trapezoidal_imgDeform( img, strength, direction ):
    return ImageOps.deform(
        img,
        TrapezoidalDistortionDeformer( strength, direction )
    )


def distort_trapezoidal_uniform( img, strength, direction ):
    return distort_trapezoidal( img, (strength, strength), direction )


def distort_trapezoidal( img, strength, direction ):
    strength = (
        strength[0] * 0.5,
        1 - (strength[1] * 0.5)
    )

    if img.mode == '1':
        img = (np.array(img) * 255).astype('uint8')
    else: 
        img = (np.array(img)).astype('uint8')

    if direction == 'bottom':
        input_pts = np.float32([
            [0, 0],
            [int(img.shape[1] * strength[0]),img.shape[0]],
            [int(img.shape[1] * strength[1]),img.shape[0]],
            [img.shape[1],0]
        ])
    elif direction == 'top':
        input_pts = np.float32([
            [int(img.shape[1] * strength[0]), 0],
            [0,img.shape[0]],
            [img.shape[1],img.shape[0]],
            [int(img.shape[1] * strength[1]), 0]
        ])
    elif direction == 'left':
        input_pts = np.float32([
            [0, int(img.shape[0] * strength[0])],
            [0, int(img.shape[0] * strength[1])],
            [img.shape[1],img.shape[0]],
            [img.shape[1], 0]
        ])
    else:
        input_pts = np.float32([
            [0, 0],
            [0, img.shape[0]],
            [img.shape[1], int(img.shape[0] * strength[1])],
            [img.shape[1], int(img.shape[0] * strength[0])]
        ])
    
    output_pts = np.float32([
        [0,0],
        [0,img.shape[0]],
        [img.shape[1],img.shape[0]],
        [img.shape[1],0]
    ])

    # Compute the perspective transform M
    M = cv2.getPerspectiveTransform(input_pts,output_pts)
    
    # Apply the perspective transformation to the image
    out = cv2.warpPerspective(img,M,(img.shape[1], img.shape[0]),flags=cv2.INTER_LINEAR)
        
    return Image.fromarray(out)