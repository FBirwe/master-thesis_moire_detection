import sys
sys.path.append('../../30_data_tools/')
from torchvision import datasets, transforms
from torchvision.transforms import v2

from helper import load_dotenv
import torch
import numpy as np
import math 
from scipy.ndimage import gaussian_filter
from PIL import Image
from time import time


dotenv = load_dotenv()

def get_radius_map():
    radius_map = torch.zeros((224,224))

    for y in range(224):
        radius_map[y,:] = torch.hypot(torch.arange(224) - 112, torch.Tensor([y - 112]))

    return radius_map


def get_fft( input_img ):
    img_torch = transforms.functional.to_tensor(input_img).squeeze(0) * 255
    ft = torch.fft.ifftshift( img_torch )
    ft = torch.fft.fft2( ft )
    ft = torch.fft.fftshift( ft )

    return ft



def limit_frequencies( fft, radius_map, inner_limit=None, outer_limit=None ):
    if (inner_limit is None) == False:
        fft[radius_map <= inner_limit] = 1

    if (outer_limit is None) == False:
        fft[radius_map >= outer_limit] = 1
    
    return fft


def get_frequency_representation( img, radius_map ):
    fft = torch.abs( limit_frequencies( get_fft(img), radius_map, inner_limit=5 ) ).reshape((1,224,224))    
    fft = transforms.functional.gaussian_blur(fft, (11,11), sigma=3)[0,:,:]

    return fft


def img_to_fft( img, radius_map ):
    fft = get_frequency_representation(img.convert('L'), radius_map)
    channel = (fft / fft.max() * 255)
    fft = torch.zeros((channel.shape[0],channel.shape[1],3))
    fft[:,:,0] = channel
    fft[:,:,1] = channel
    fft[:,:,2] = channel

    return fft


def get_datasets( dataset_name, dataset_base_directory=dotenv['TILE_DATASET_DIR'], spatial_img=True ):
    """
        Lädt die vorhandenen Datensets ein und
        transformiert sie so, dass pyTorch Modelle
        damit gut arbeiten können
    """
    dataset_directory = dataset_base_directory / dataset_name

    available_datasets = {}
    for entry in dataset_directory.iterdir():
        if entry.is_dir() and entry.name.startswith('.') == False:
            available_datasets[entry.name] = {
                'path' : entry
            }

    # load transformations
    transformations = [
        transforms.ToTensor()
    ]
    if spatial_img == False:
        radius_map = get_radius_map()

        transformations.insert(0, transforms.Lambda(lambda img: img_to_fft(img, radius_map)))

    # Nur beim Training sollen die Augmentierungen angewandt werden
    train_transformations = [
        transforms.RandomApply([v2.ColorJitter(brightness=0.5,contrast=0.5)], p=0.5),
        # transforms.RandomApply([v2.RandomRotation(20)], p=0.5),
        # transforms.RandomApply([v2.RandomResize(224, 448)], p=0.5),
        # v2.CenterCrop(224)
    ]

    # Create transform function
    data_transformation = transforms.Compose(transformations)
    data_train_transformation = transforms.Compose([
        *train_transformations,
        *transformations
    ])

    for key in available_datasets:
        if key == 'train':
            available_datasets[key]['dataset'] = datasets.ImageFolder(available_datasets[key]['path'], data_train_transformation)
        else:
            available_datasets[key]['dataset'] = datasets.ImageFolder(available_datasets[key]['path'], data_transformation)

        available_datasets[key]['dataloader'] = torch.utils.data.DataLoader(available_datasets[key]['dataset'], batch_size=64, shuffle=True, num_workers=0)

    # print infos
    for key in available_datasets:
        print(f'{ key } size', len(available_datasets[key]['dataset']))

    print('class names', available_datasets['train']['dataset'].classes)

    return available_datasets


def run_model(dataloader, model, device, loss_fn, dataset, metrics=[], optimizer=None, mode='train', log_intervall=10, train_logger=None ):
    start_timestamp = time()

    if mode == 'train':
        model.train()
    else:
        model.eval()
    train_logger.log_mode( mode )
    
    running_loss = []
    running_metrics = { m[0] : [] for m in metrics }

    for batch, (X, y) in enumerate(dataloader):
        X, y = X.to(device), y.to(device)

        if mode == 'train':
            pred = model(X)
        else:
            with torch.no_grad():
                pred = model(X)

        loss = loss_fn(pred, y)

        running_loss.append( float(loss.item()) )
        for metric_name,metric_fn in metrics:
            running_metrics[metric_name].append( float(metric_fn(pred,y)) )

        # Backpropagation.
        if mode == 'train':
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

        if batch % log_intervall == 0 or batch == len(dataloader) - 1:
            loss, current = loss.item(), batch

            mean_loss = sum(running_loss) / len(running_loss)
            metric_string = f"[{current + 1} / {len(dataloader)}] loss: {mean_loss:3f}"

            if train_logger:
                train_logger.log_metric( dataset, "loss", f"{loss:3f}", step=(batch // log_intervall))
    
            for i in range(len(metrics)):
                metric_name, _ = metrics[i]
                mean_metric = sum(running_metrics[metric_name]) / len(running_metrics[metric_name])
                if train_logger:
                    train_logger.log_metric( dataset, metric_name, f"{mean_metric:3f}", step=(batch // log_intervall))
                metric_string += f" {metric_name}: {mean_metric:3f}"

            endchar = "\r" if batch != len(dataloader) - 1 else "\n"
            print(metric_string, end=endchar)

    end_timestamp = time()
    print(f'run took { end_timestamp - start_timestamp }s')


def train(dataloader, dataset, model, device, loss_fn, optimizer, metrics=[], log_intervall=10, train_logger=None ):
    run_model(
        dataloader,
        model,
        device,
        loss_fn,
        dataset,
        optimizer=optimizer,
        metrics=metrics,
        train_logger=train_logger,
        mode='train',
        log_intervall=log_intervall
    )

def validate(dataloader, dataset, model, device, loss_fn, metrics=[], log_intervall=10, train_logger=None ):
    run_model(
        dataloader,
        model,
        device,
        loss_fn,
        dataset,
        optimizer=None,
        metrics=metrics,
        train_logger=train_logger,
        mode="val",
        log_intervall=log_intervall
    )
