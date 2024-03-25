from PIL import Image
import math
from random import shuffle
import numpy as np
import csv
from enum import Enum
from tqdm import tqdm
from pathlib import Path


class DOT_SHAPE(Enum):
    LINE = 1
    CIRCLE = 2
    DIAMOND = 3


def read_threshold( dot_shape, screen_size ):
    if dot_shape == DOT_SHAPE.LINE:
        dot_shape_name = 'line'
    elif dot_shape == DOT_SHAPE.CIRCLE:
        dot_shape_name = 'circle'
    elif dot_shape == DOT_SHAPE.DIAMOND:
        dot_shape_name = 'diamond'
    
    csv_path = Path(__file__).parent / f'{dot_shape_name}_{screen_size}.csv'
    with csv_path.open() as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';', quotechar='"')
        rows = []
    
        for row in csv_reader:
            rows.append([float(val) for val in row])

    return np.array(rows)


class RasterImageProcessor:
    def __init__( self, dot_shape, screen_size ):
        self.dot_shape = dot_shape
        self.screen_size = screen_size
        self.threshold_map = read_threshold( dot_shape, screen_size )

    def convert_tile( self, coverage ):
        tile = np.zeros((self.screen_size,self.screen_size))
        max_index = self.screen_size ** 2 * coverage
        tile[self.threshold_map <= max_index] = 1
        
        return tile
    

    def screen_image( self, source_img, source_resolution, target_resolution ):
        source_img = np.array(source_img)
        screen_size_source = round(source_resolution / 150)

        out_img = np.zeros((
            round(source_img.shape[0] / source_resolution * target_resolution),
            round(source_img.shape[1] / source_resolution * target_resolution)
        ))

        for x in tqdm(range( math.ceil(source_img.shape[1] / screen_size_source) )):
            for y in range( math.ceil(source_img.shape[0] / screen_size_source) ):
                source_tile = source_img[
                    y * screen_size_source:(y+1)*screen_size_source,
                    x * screen_size_source:(x+1)*screen_size_source
                ]

                coverage = source_tile.mean() / 255
                
                out_tile = self.convert_tile( coverage )
                out_img[
                    y * self.screen_size:(y+1) * self.screen_size,
                    x * self.screen_size:(x+1) * self.screen_size
                ] = out_tile

        return Image.fromarray(out_img.astype('bool'))


if __name__ == '__main__':
    print(  )