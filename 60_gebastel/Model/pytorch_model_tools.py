import sys
sys.path.append('../../30_data_tools/')
from torchvision import datasets, transforms
from helper import load_dotenv
import torch

dotenv = load_dotenv()

def get_datasets( dataset_directory=dotenv['TILE_DATASET_DIR'] ):
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
    transforms_data = transforms.Compose([
        # transforms.ColorJitter(brightness=0.5,contrast=0.5),
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
