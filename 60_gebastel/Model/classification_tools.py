import numpy as np


def cut_img_into_tiles( img, tile_size=224 ):
    tiles = []    
    left = 0
    top = 0
    
    while left < img.size[0] or top < img.size[1]:
        tile = img.crop((
            left,top,
            left+tile_size,top+tile_size
        ))
        tiles.append( ((left,top),tile) )
    
        if left < img.size[0]:
            left += round(tile_size / 2)
        elif top < img.size[1]:
            left = 0
            top += tile_size
        else:
            break

    return tiles


def preclassifier( tiles, margin=0.03, min_midtone_share=0.05 ):
    tiles_out = []
    
    for pos,tile in tiles:
        is_relevant = False
        np_tile = 1 - np.array(tile) / 255
        
        for i in range( np_tile.shape[2] ):
            sep = np_tile[:,:,i]
            midtone_share = sep[(sep > margin) & (sep < (1 - margin))].shape[0] / (sep.shape[0] * sep.shape[1])
        
            if midtone_share > min_midtone_share:
                is_relevant = True
                break

        if is_relevant:
            tiles_out.append((pos,tile))

    return tiles_out