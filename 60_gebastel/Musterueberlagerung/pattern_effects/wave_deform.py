import math
from PIL import ImageOps, Image


class WaveDeformer:
    def __init__(self, wave_length, wave_depth) -> None:
        self.wave_length = wave_length
        self.wave_depth = wave_depth

    def transform(self, x, y):
        y = y + self.wave_depth * math.sin(x * math.pi * 0.5 / self.wave_length)
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
        gridspace = min(int(self.wave_length * 0.25), 15)

        target_grid = []
        for x in range(0, self.w, gridspace):
            for y in range(0, self.h, gridspace):
                target_grid.append((x, y, x + gridspace, y + gridspace))

        source_grid = [self.transform_rectangle(*rect) for rect in target_grid]

        return [t for t in zip(target_grid, source_grid)]


def wave_deform( pattern_img, wave_length, wave_depth ):
    return ImageOps.deform(
        pattern_img,
        WaveDeformer(wave_length, wave_depth)
    )