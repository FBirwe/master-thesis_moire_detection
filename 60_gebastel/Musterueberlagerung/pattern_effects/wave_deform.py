import math
from PIL import ImageOps, Image


class WaveDeformer:
    def __init__(self, wave_configs ) -> None:
        self.wave_configs = wave_configs
        # self.wave_length = wave_length
        # self.wave_depth = wave_depth

    def transform(self, x, y):
        y = y + sum([
            wave_depth * math.sin( x / wave_length * 2 * math.pi )
            for wave_length, wave_depth in self.wave_configs
        ])
        return x, y

    def transform_rectangle(self, x0, y0, x1, y1):
        return (
            *self.transform(x0, y0),
            *self.transform(x0, y1),
            *self.transform(x1, y1),
            *self.transform(x1, y0),
        )

    def getmesh(self, img):
        self.w, self.h = img.size
        min_wave_length = min([wave_length for wave_length, wave_depth in self.wave_configs])
        gridspace = min(int(min_wave_length * (1/16)), 15)

        target_grid = []
        for x in range(0, self.w, gridspace):
            for y in range(0, self.h, gridspace):
                target_grid.append((x, y, x + gridspace, y + gridspace))

        source_grid = [self.transform_rectangle(*rect) for rect in target_grid]

        return [t for t in zip(target_grid, source_grid)]


def wave_deform( pattern_img, wave_configs ):
    return ImageOps.deform(
        pattern_img,
        WaveDeformer( wave_configs )
    )


if __name__ == '__main__':
    img = Image.new('L', (500,500))
    waveDeformer = WaveDeformer( [(100,50)] )

    print( waveDeformer.getmesh(img) )