import sys
sys.path.append('../../30_data_tools')

from PIL import Image
from tqdm import tqdm
from helper import load_dotenv
import torch
from torchvision import models, transforms
from file_interaction import download_blob, upload_buffer
from io import BytesIO
import pandas as pd
import json
from datetime import datetime
from pytorch_model_tools import img_to_fft, get_radius_map


dotenv = load_dotenv()
BATCH_SIZE = 64


def load_experiment( experiment_name ):
    json_buffer = download_blob( f'train_logs/{ experiment_name }.json' )
    data = json.loads( json_buffer.getvalue() )
    data['start_timestamp'] = datetime.fromisoformat(data['start_timestamp'])

    if 'end_timestamp' in data:
        data['end_timestamp'] = datetime.fromisoformat(data['end_timestamp'])

    for t in data['tracked_metrics']:
        t['timestamp'] = datetime.fromisoformat(t['timestamp'])
        t['value'] = float(t['value'])
    
    return data


def load_model( model_name ):
    bytesStream = download_blob( f'models/{ model_name }.pth' )

    if torch.cuda.is_available():
        model = torch.load( BytesIO(bytesStream.getvalue()) )
    else:
        model = torch.load( BytesIO(bytesStream.getvalue()), map_location=torch.device('cpu') )

    model.eval()
    return model


def convert_results_to_df( tile_paths, results ):
    data = []
    for i in range(len(tile_paths)):
        data.append({
            'tile_name' : tile_paths[i].name,
            'label' : tile_paths[i].parent.name,
            'dataset' : tile_paths[i].parent.parent.name,
            'result_moire' : float(results[i][0]),
            'result_no_moire' : float(results[i][1])
        })

    return pd.DataFrame.from_dict(data)


def load_dataset( dataset_name, datasets=None ):
    # Daten werden geladen
    dataset_path = dotenv['TILE_DATASET_DIR'] / dataset_name
    tile_paths = []

    if dataset_path.exists() == False:
        raise Exception("dataset not found")

    # Wenn datasets=None, dann alle Datensets prüfen
    if datasets is None:
        tile_paths = list(dataset_path.glob('./**/*.jpg'))
    else:
        for dataset in datasets:
            tile_paths += list((dataset_path / dataset).glob('./**/*.jpg'))

    return tile_paths


def cal_model_results( tile_paths, model, data_type="spatial" ):
    # Datenset wird geladen
    current_batch = []
    results = []

    def process_batch( batch ):
        # Prüfung wird durchgeführt
        with torch.no_grad():
            if torch.cuda.is_available():
                batch = batch.cuda()

            pred = model(batch)
            return pred.cpu().numpy().tolist()

    if data_type == 'spatial':
        transform = transforms.ToTensor()
    else:
        radius_map = get_radius_map()
        transform = transforms.Compose([
            transforms.Lambda(lambda img: img_to_fft(img, radius_map)),
            transforms.ToTensor()
        ])

    for tile_path in tqdm(tile_paths):
        with Image.open(tile_path) as tile:
            current_batch.append(transform(tile))
    
        if len(current_batch) == BATCH_SIZE:
            results += process_batch(torch.stack(current_batch))
            current_batch = []

    results += process_batch(torch.stack(current_batch))
    return results


def main():
    model_name = sys.argv[1]
    dataset_name = sys.argv[2]
    experiment_data = load_experiment( model_name )
    
    if len(sys.argv) < 4:
        datasets = None
    else:
        datasets = sys.argv[3].split(";")

    print("start process")
    model = load_model( model_name )
    print("model loaded")

    tile_paths = load_dataset( dataset_name, datasets=datasets )
    print("dataset loaded")

    results = cal_model_results( tile_paths, model, data_type=experiment_data['hyper_parameters']['data_type'] )
    print("results calculated")

    df = convert_results_to_df( tile_paths, results )

    # upload df
    stream = BytesIO()
    df.to_pickle( stream )

    upload_buffer( stream.getbuffer(), f'model_results/{ model_name }_{ dataset_name }.pkl' )
    print("process finished")


if __name__ == '__main__':
    main()