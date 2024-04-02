import sys
sys.path.append('../../30_data_tools/')
# Set up CUDA in OS
import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
# Import libabries
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

dotenv = load_dotenv()

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f'device used: { device }')


available_datasets = get_datasets()

model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
num_features = model.fc.in_features 
# Add a fully-connected layer for classification
model.fc = nn.Sequential(
    nn.Linear(num_features, 2),
    nn.Sigmoid()
)
model = model.to(device)

torch.manual_seed(42)
torch.cuda.manual_seed(42)

epochs = 15
learning_rate = 0.001
loss_fn = nn.CrossEntropyLoss()
accuracy_fn = Accuracy(task="multiclass", num_classes=2).to(device)
recall_fn = Recall(task="multiclass", average='macro', num_classes=2).to(device)
precision_fn = Precision(task="multiclass", average='macro', num_classes=2).to(device)
optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate, momentum=0.9)

train_logger = TrainLogger( 'resnet50' )

with train_logger.start_run():
    train_logger.log_hyperparams({
        "epochs": epochs,
        "learning_rate": learning_rate,
        "batch_size": 64,
        "loss_function": loss_fn.__class__.__name__,
        "metric_function": accuracy_fn.__class__.__name__,
        "optimizer": "SGD",
        "device" : device
    })

    train_logger.log_summary(str(summary(model)))

    for t in range(epochs):
        print(f"Epoch {t+1} -------------------------------")
        # train(available_datasets['train']['dataloader'], model, device, loss_fn, optimizer, train_logger=train_logger, metrics=[('accuracy',accuracy_fn), ('recall',recall_fn), ('precision',precision_fn)] )
        
        # print("validate")
        # validate(available_datasets['val']['dataloader'], model, device, loss_fn, train_logger=train_logger, metrics=[('accuracy',accuracy_fn), ('recall',recall_fn), ('precision',precision_fn)] )


    train_logger.save_model( model )