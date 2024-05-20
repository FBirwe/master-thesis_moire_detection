import sys
sys.path.append('../../30_data_tools/')
# Set up CUDA in OS
import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
# Import libabries
from file_interaction import download_blob
import torch
import torch.nn as nn
from torchmetrics import Accuracy, Recall, Precision
from torchinfo import summary
from torchvision import *
import torchvision.transforms as T
from torchvision import datasets, models, transforms
from tqdm.auto import tqdm
from helper import load_dotenv
from pytorch_model_tools import get_datasets, train, validate
from train_logger import TrainLogger
from pathlib import Path
import json
import sys
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
from io import BytesIO
from ffc_resnet import ffc_resnet50


"""
    Durch die Ausführung dieses Scriptes wird der Trainingsprozess für ein Modell
    unter Verwendung der Parameter aus der übergebenen JSON-Datei ausgeführt.
"""


def load_config():
    if len(sys.argv) <= 1:
        raise Exception('no config-path provided')

    json_path = Path(sys.argv[1])

    if json_path.exists() == False:
        raise Exception('json does not exists')

    with json_path.open() as json_file:
        config = json.load( json_file )

    for key in ['model_architecture']:
        if key not in config:
            raise Exception(f'mandatory key { key } not provided')
 
    return config


def main():
    try:
        config = load_config()
        dotenv = load_dotenv()

        device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f'device used: { device }')

        available_datasets = get_datasets( config['dataset_name'], spatial_img=config['spatial_train_data'] )

        # model laden
        if 'continue_from' in config:
            bytesStream = download_blob( f'models/{ config["continue_from"] }.pth' )
            model = torch.load( BytesIO(bytesStream.getvalue()) )
            print("model loaded")
        else:
            if config['model_architecture'] == 'Resnet50':
                model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)

                num_features = model.fc.in_features 
                # Add a fully-connected layer for classification
                model.fc = nn.Sequential(
                    nn.Linear(num_features, 2),
                    nn.Softmax(dim=1)
                )
            elif config['model_architecture'] == 'FFCResnet50':
                model = ffc_resnet50( pretrained=True )

                num_features = model.fc.in_features 
                # Add a fully-connected layer for classification
                model.fc = nn.Sequential(
                    nn.Linear(num_features, 2),
                    nn.Softmax(dim=1)
                )
            elif config['model_architecture'] == 'MobileNetV3':
                model = models.mobilenet_v3_small( weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 ) 
                model.classifier = nn.Sequential(
                    nn.Linear(model.classifier[0].in_features, 2),
                    nn.Softmax(dim=1)
                )

        model = model.to(device)

        torch.manual_seed(42)
        torch.cuda.manual_seed(42)

        loss_fn = nn.CrossEntropyLoss()
        accuracy_fn = Accuracy(task="multiclass", num_classes=2).to(device)
        recall_fn = Recall(task="multiclass", average='macro', num_classes=2).to(device)
        precision_fn = Precision(task="multiclass", average='macro', num_classes=2).to(device)

        if config['optimizer'] == 'adam':
            optimizer = torch.optim.Adam(model.parameters(), lr=config['learning_rate'], betas=(0.9, 0.999), eps=1e-08, weight_decay=0)
        else:
            optimizer = torch.optim.SGD(model.parameters(), lr=config['learning_rate'], momentum=0.9)

        train_logger = TrainLogger( config['model_architecture'] )

        with train_logger.start_run():
            train_logger.log_hyperparams({
                "dataset_name" : config['dataset_name'],
                "data_type" : "spatial" if config['spatial_train_data'] else "frequency",
                "epochs": config['n_epochs'],
                "learning_rate": config['learning_rate'],
                "batch_size": 64,
                "loss_function": loss_fn.__class__.__name__,
                "metric_functions": [accuracy_fn.__class__.__name__,recall_fn.__class__.__name__,precision_fn.__class__.__name__],
                "optimizer": config['optimizer'],
                "device" : device
            })

            train_logger.log_summary(str(summary(model)))

            for t in range(config['n_epochs']):
                train_logger.set_epoch(t+1)
                print(f"Epoch {t+1} -------------------------------")
                train(available_datasets['train']['dataloader'], 'train', model, device, loss_fn, optimizer, train_logger=train_logger, metrics=[('accuracy',accuracy_fn), ('recall',recall_fn), ('precision',precision_fn)] )
                
                print("validate")
                validate(available_datasets['val']['dataloader'], 'val', model, device, loss_fn, train_logger=train_logger, metrics=[('accuracy',accuracy_fn), ('recall',recall_fn), ('precision',precision_fn)] )

                print("validate - real val")
                validate(available_datasets['real_val']['dataloader'], 'real_val', model, device, loss_fn, train_logger=train_logger, metrics=[('accuracy',accuracy_fn), ('recall',recall_fn), ('precision',precision_fn)] )

                train_logger.save_model( model )

                print("")

    except Exception as e:
        print(e)
    

if __name__ == '__main__':
    main()