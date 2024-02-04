import numpy as np
import math
from PIL import Image
from scipy.special import expit as logistic


def interpolate_radius( r, radius, c, is_blow_up=True ):
    interpolation_factor = r / radius
    direction_factor = 1 if is_blow_up else -1
    return (interpolation_factor * r + (1.0 - interpolation_factor) * c * math.sqrt(r)) * direction_factor
    #return math.sin(r * math.pi * 2 / radius) * c * -1

# def interpolate_radius( r, radius, c, is_blow_up=True ):
#     direction_factor = 1 if is_blow_up else -1
#     factor = ((math.sin(2 * math.pi * r / radius))) * 0.5

#     return r + factor * radius * direction_factor


def radial_deformation( img, radius, center, c, is_blow_up=True ):
    img_out = img.copy()
    
    for x_coor in range(center[0] - radius, center[0] + radius):
        for y_coor in range(center[1] - radius, center[1] + radius):
            x = x_coor - center[0]
            y = y_coor - center[1]
        
            r = math.sqrt(x**2 + y**2)
            alpha = math.atan2(y, x)
            degrees = (alpha * 180.0) / math.pi

            # Wenn sich der Pixel außerhalb des Kreises befindet
            # soll der Originalpixel übernommen werden
            if r <= radius:
                r = interpolate_radius( r, radius, c, is_blow_up=is_blow_up )

                alpha = (degrees * math.pi) / 180.0
                newY = math.floor(r * math.sin(alpha)) + center[0]
                newX = math.floor(r * math.cos(alpha)) + center[1]

                if newX < img_out.shape[1] and newX >= 0 and newY < img_out.shape[0] and newY >= 0:
                    img_out[
                        newY,
                        newX
                    ] = img[
                        y_coor,
                        x_coor
                    ]

    return Image.fromarray(img_out).convert('L')


def radial_deformation_centered( img, c, is_blow_up ):
    """
        Führt eine runde Verzerrung auf das Bild aus
        Der Faktor C steuert die Intensität des Verlaufs.
        Der Wert "is_blow_up" steuert, ob das Bild kreisformig
        zusammengezogen wird doer expandiert.
    """
    img = np.array(img)
    center = (
        int(img.shape[1] / 2),
        int(img.shape[0] / 2)
    )
    radius = max(center)

    # der Faktor c wird zunächst statisch auf die Wurzel des Radiuses gelegt, um
    # die "verzerrungswurst" auf den Bildrand zu legen.
    return radial_deformation( img, radius, center, math.sqrt(radius), is_blow_up=is_blow_up )


def blow_up( img, c ):
    """
        Expandiert das gesamte Bild kreisförmig ausgehend von der Mitte
    """
    return radial_deformation_centered( img, c, True )


def contract( img, c ):
    return radial_deformation_centered( img, c, False )


def blow_up_region( img, radius, center, c ):
    return radial_deformation( np.array(img), radius, center, math.sqrt(radius) * c, is_blow_up=True )


def contract_region( img, radius, center, c ):
    return radial_deformation( np.array(img), radius, center, math.sqrt(radius) * c, is_blow_up=False )
