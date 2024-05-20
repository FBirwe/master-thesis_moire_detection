import numpy as np
from tqdm.auto import tqdm
import torch
from torchvision import transforms
from PIL import Image


def cut_img_into_tiles( orig_img, source_dpi, resolutions, tile_size=224 ):
    tiles = []   

    for resolution in resolutions:
        img = orig_img.resize((
            round(orig_img.size[0] * (resolution / source_dpi)),
            round(orig_img.size[1] * (resolution /source_dpi))
        ))

        left = 0
        top = 0
        
        while left < img.size[0] or top < img.size[1]:
            tile = img.crop((
                left,top,
                left+tile_size,top+tile_size
            ))
            tiles.append( (resolution, (left,top), tile) )
        
            if left < img.size[0]:
                left += tile_size
            elif top < img.size[1]:
                left = 0
                top += tile_size
            else:
                break

    return tiles


def classifier( tiles, model, tile_size=224, max_batch_size=64 ):
    batch_start = 0
    predictions = []
    
    with tqdm(total=len(tiles)) as pbar:
        while batch_start < len(tiles):
            tile_selection = tiles[batch_start:batch_start+max_batch_size]
            batch = torch.zeros([len(tile_selection), 3, tile_size, tile_size], dtype=torch.float32)
        
            for i in range(len(tile_selection)):
                transform = transforms.Compose([transforms.PILToTensor()])                
                batch[i,:,:,:] = transform(Image.fromarray(np.array(tile_selection[i][2])[:,:,3]).convert('RGB')) / 255 
            
            model.eval()

            with torch.no_grad():
                model_predictions = model(batch)
                predictions += [(*tile_selection[i],model_predictions[i],int(torch.argmax(model_predictions[i]))) for i in range(len(model_predictions))]
    
            batch_start += max_batch_size
            pbar.update(len(tile_selection))

    return predictions


def preclassifier( tiles, margin=0.03, min_midtone_share=0.05 ):
    tiles_out = []
    
    for resolution,pos,tile in tiles:
        is_relevant = False
        np_tile = 1 - np.array(tile) / 255
        
        for i in range( np_tile.shape[2] ):
            sep = np_tile[:,:,i]
            midtone_share = sep[(sep > margin) & (sep < (1 - margin))].shape[0] / (sep.shape[0] * sep.shape[1])
        
            if midtone_share > min_midtone_share:
                is_relevant = True
                break

        if is_relevant:
            tiles_out.append((resolution,pos,tile))

    return tiles_out