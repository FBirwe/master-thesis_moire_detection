from pathlib import Path
import sys
sys.path.append( (Path(__file__) / '..' / '..' / '..' / '30_data_tools' ).resolve() )
from datetime import datetime
from time import sleep
import json
from helper import load_dotenv
from file_interaction import upload_buffer, get_blobs
import io
import torch


class TrainLogger:
    def __init__(self, target_model ) -> None:
        self.experiment_name = ""
        self.target_model = target_model
        self.active_run = None
        self.hyper_params = {}
        self.tracked_metrics = []
        self.model_summary = ''
        self.dotenv = load_dotenv()
        self.current_mode = "undefined"
        self.start_timestamp = None
        self.end_timestamp = None


    def log_hyperparams( self, hyper_params ):
        self.hyper_params = hyper_params

    def log_mode( self, mode ):
        self.current_mode = mode

    def start_run( self ):
        return ActiveRun( self )

    def write_log_summary( self ):
        out = {
            'start_timestamp' : self.start_timestamp.isoformat(),
            'experiment_name' : self.experiment_name,
            'target_model' : self.target_model,
            'hyper_parameters' : self.hyper_params,
            'model_summary' : self.model_summary,
            'tracked_metrics' : self.tracked_metrics
        }

        if self.end_timestamp:
            out['end_timestamp'] = self.end_timestamp.isoformat()

        json_data = io.StringIO()
        json_data.write( json.dumps(out) )
        json_path = f'train_logs/{ self.experiment_name }.json'

        upload_buffer(
            json_data.getvalue(),
            json_path
        )
        json_data.close()


    def log_metric( self, metric_name, value, step=None ):
        metric_log_entry = {
            'metric_name' : metric_name,
            'value' : value,
            'timestamp' : datetime.now().isoformat(),
            'mode' : self.current_mode
        }

        if (step is None) == False:
            metric_log_entry['step'] = step

        self.tracked_metrics.append(metric_log_entry)
        self.write_log_summary()


    def log_summary( self, summary_string ):
        self.model_summary = summary_string

    def save_model( self, model ):
        modelfile = io.BytesIO()
        torch.save(model, modelfile )

        # buffer hochladen
        upload_buffer(
            modelfile.getvalue(),
            f'models/{ self.experiment_name }.pth'
        )



class ActiveRun:
    def __init__(self, train_logger ) -> None:
        self.train_logger = train_logger
        self.train_logger.start_timestamp = datetime.now()

        i = 1
        experiment_name = f"{ self.train_logger.start_timestamp.strftime('%Y-%m-%d') }_{ self.train_logger.target_model }_{ str(i).zfill(3) }"

        while len(get_blobs( filter=f'train_logs/{ experiment_name }.json')) > 0:
            i += 1
            experiment_name = f"{ self.train_logger.start_timestamp.strftime('%Y-%m-%d') }_{ self.train_logger.target_model }_{ str(i).zfill(3) }"

        self.train_logger.experiment_name = experiment_name

    def __enter__( self ):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.train_logger.end_timestamp = datetime.now()
        self.train_logger.write_log_summary()

        return exc_type is None


if __name__ == '__main__':
    print(  )