from PIL import ImageOps


class PillowDeformer:
    def __init__( self, pillow_depth_x, pillow_depth_y ):
        self.pillow_depth_x = pillow_depth_x
        self.pillow_depth_y = pillow_depth_y
    

    def get_box( self, is_left, is_top ):
        x1 = 0 if is_left else self.w // 2
        x2 = self.w // 2 if is_left else self.w

        y1 = 0 if is_top else self.h // 2
        y2 = self.h // 2 if is_top else self.h

        target_grid = [
            x1, y1, x2, y2
        ]

        source_grid = [
            x1, y1,
            x1, y2,
            x2, y2,
            x2, y1
        ]

        if is_left and is_top:
            source_grid[2] = self.w * self.pillow_depth_x * -1
            source_grid[7] = self.h * self.pillow_depth_y * -1
        if is_left and is_top == False:
            source_grid[0] = self.w * self.pillow_depth_x * -1
            source_grid[5] = self.h * (self.pillow_depth_y + 1)
        if is_left == False and is_top:
            source_grid[4] = self.w * (self.pillow_depth_x + 1)
            source_grid[1] = self.h * self.pillow_depth_y * -1
        if is_left == False and is_top == False:
            source_grid[6] = self.w * (self.pillow_depth_x + 1)
            source_grid[3] = self.h * (self.pillow_depth_y + 1)

        
        return target_grid, source_grid
    
    
    def getmesh(self, img):
        self.w, self.h = img.size

        return [
            self.get_box( True, True ),
            self.get_box( True, False ),
            self.get_box( False, True ),
            self.get_box( False, False ) 
        ]
    

def pillow_deform( pattern_img, pillow_depth_x, pillow_depth_y ):
    return ImageOps.deform(
        pattern_img,
        PillowDeformer( pillow_depth_x, pillow_depth_y )
    )