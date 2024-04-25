import sys
sys.path.append('../../30_data_tools/')
from torchvision import datasets, transforms
from helper import load_dotenv
import torch
import numpy as np
import math 
from scipy.ndimage import gaussian_filter
from PIL import Image

dotenv = load_dotenv()

def get_fft( input_img ):
    ft = np.fft.ifftshift(np.array(input_img))
    ft = np.fft.fft2(ft)
    ft = np.fft.fftshift(ft)
    
    return ft


def limit_frequencies( fft, inner_limit=None, outer_limit=None ):
    center = (fft.shape[1] / 2, fft.shape[0] / 2)
    for y in range(fft.shape[0]):
        for x in range(fft.shape[1]):
            r = math.sqrt( abs(center[0] - x) ** 2 + abs(center[1] - y) ** 2 )
            
            if outer_limit is not None and r > outer_limit:
                fft[y,x] = 1
    
            if inner_limit is not None and r < inner_limit:
                fft[y,x] = 1

    return fft

def get_frequency_representation( img ):
    fft = np.abs( limit_frequencies( get_fft(img), inner_limit=5 ) )
    fft = gaussian_filter(fft, sigma=3)

    return fft


def img_to_fft( img ):
    fft = get_frequency_representation(img.convert('L'))
    channel = (fft / fft.max() * 255).astype('uint8')
    fft = np.zeros((channel.shape[0],channel.shape[1],3)).astype('uint8')
    fft[:,:,0] = channel
    fft[:,:,1] = channel
    fft[:,:,2] = channel

    return fft


def get_datasets( dataset_directory=dotenv['TILE_DATASET_DIR'], spatial_img=True ):
    """
        Lädt die vorhandenen Datensets ein und
        transformiert sie so, dass pyTorch Modelle
        damit gut arbeiten können
    """
    available_datasets = {}
    for entry in dataset_directory.iterdir():
        if entry.is_dir() and entry.name.startswith('.') == False:
            available_datasets[entry.name] = {
                'path' : entry
            }

    # Create transform function
    if spatial_img:
        transforms_data = transforms.Compose([
            transforms.ColorJitter(brightness=0.5,contrast=0.5),
            transforms.ToTensor(),
            # transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]) # normalization
        ])
    else:
        transforms_data = transforms.Compose([
            transforms.ColorJitter(brightness=0.5,contrast=0.5),
            transforms.Lambda(img_to_fft),
            transforms.ToTensor(),
            # transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]) # normalization
        ])


    for key in available_datasets:
        available_datasets[key]['dataset'] = datasets.ImageFolder(available_datasets[key]['path'], transforms_data)
        available_datasets[key]['dataloader'] = torch.utils.data.DataLoader(available_datasets[key]['dataset'], batch_size=64, shuffle=True, num_workers=0)

    # print infos
    for key in available_datasets:
        print(f'{ key } size', len(available_datasets[key]['dataset']))

    print('class names', available_datasets['train']['dataset'].classes)

    return available_datasets


def run_model(dataloader, model, device, loss_fn, metrics=[], optimizer=None, mode='train', log_intervall=10, train_logger=None ):
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
                train_logger.log_metric("loss", f"{loss:3f}", step=(batch // log_intervall))
    
            for i in range(len(metrics)):
                metric_name, _ = metrics[i]
                mean_metric = sum(running_metrics[metric_name]) / len(running_metrics[metric_name])
                if train_logger:
                    train_logger.log_metric(metric_name, f"{mean_metric:3f}", step=(batch // log_intervall))
                metric_string += f" {metric_name}: {mean_metric:3f}"

            endchar = "\r" if batch != len(dataloader) - 1 else "\n"
            print(metric_string, end=endchar)


def train(dataloader, model, device, loss_fn, optimizer, metrics=[], log_intervall=10, train_logger=None ):
    run_model(
        dataloader,
        model,
        device,
        loss_fn,
        optimizer=optimizer,
        metrics=metrics,
        train_logger=train_logger,
        mode='train',
        log_intervall=log_intervall
    )

def validate(dataloader, model, device, loss_fn, metrics=[], log_intervall=10, train_logger=None ):
    run_model(
        dataloader,
        model,
        device,
        loss_fn,
        optimizer=None,
        metrics=metrics,
        train_logger=train_logger,
        mode="val",
        log_intervall=log_intervall
    )
