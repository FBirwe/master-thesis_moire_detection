from azure.storage.blob import BlobClient, ContainerClient, BlobServiceClient
import io
from helper import load_dotenv, get_pdf_page_processing_status
from datetime import datetime

dotenv = load_dotenv()


def get_related_filepath( job, variant_name, filename ):
    # file liegt on Prem
    for dir_path in dotenv['DATA_DIRS']:
        filepath = dir_path / job / variant_name / filename

        if filepath.exists():
            return (str(filepath.resolve()), 'local')
        
    # file liegt in azure
    blob_path = f'data/{ job }/{ variant_name }/{ filename }'

    if blob_exists( blob_path ):
        return (blob_path, 'azure')


def blob_exists( blob_path ):
    return len( get_blobs( blob_path ) ) > 0


def copy_blob( source_file_path, target_file_path ):
    #Source
    blob_service_client = BlobServiceClient.from_connection_string(dotenv['AZURE_CONNECTION_STRING'])
    source_blob = (f"https://{dotenv['AZURE_ACCOUNT_NAME']}.blob.core.windows.net/{dotenv['AZURE_CONTAINER_NAME']}/{source_file_path}")

    # Target
    copied_blob = blob_service_client.get_blob_client(dotenv['AZURE_CONTAINER_NAME'], target_file_path)
    copied_blob.start_copy_from_url(source_blob)


def upload_file( filepath, prefix_path, filename=None ):
    if filename == None:
        filename = filepath.name

    blob = BlobClient.from_connection_string(conn_str=dotenv['AZURE_CONNECTION_STRING'], container_name=dotenv['AZURE_CONTAINER_NAME'], blob_name=f"{ prefix_path }{ filename }")

    with filepath.open("rb") as data:
         blob.upload_blob(
             data,
             overwrite=True,
             connection_timeout=600
         )


def upload_buffer( buffer, blob_path ):
    blob = BlobClient.from_connection_string(conn_str=dotenv['AZURE_CONNECTION_STRING'], container_name=dotenv['AZURE_CONTAINER_NAME'], blob_name=blob_path)

    blob.upload_blob(
        buffer,
        overwrite=True,
        connection_timeout=600
    )

def download_blob( blob_name ):
    blob = BlobClient.from_connection_string(conn_str=dotenv['AZURE_CONNECTION_STRING'], container_name=dotenv['AZURE_CONTAINER_NAME'], blob_name=blob_name)
    stream = io.BytesIO()

    blob.download_blob().readinto(stream)
    return stream


def upload_batch( data, task_type ):
    stream = io.BytesIO()
    data.to_pickle( stream )

    upload_buffer( stream.getbuffer(), f'batches/{ task_type }.{ round(datetime.now().timestamp()) }.pkl' )


def get_batch_files( batch_type=None ):
    blobs = get_blobs( filter='batches/' )

    if batch_type is not None:
        blobs = [b for b in blobs if b.split('/')[-1].startswith(batch_type)]

    return blobs


def get_blobs( filter=None ):
    container = ContainerClient.from_connection_string(conn_str=dotenv['AZURE_CONNECTION_STRING'], container_name=dotenv['AZURE_CONTAINER_NAME'])
    
    if filter:
        return list(container.list_blob_names( name_starts_with=filter ))

    return list(container.list_blob_names())


def get_data_files():
    azure_files = [(blob_path, 'azure') for blob_path in get_blobs( filter='data/')]

    local_files = []

    for data_dir in dotenv['DATA_DIRS']:
        local_files += [(entry, 'local') for entry in data_dir.glob('./**/*') if entry.is_dir() == False and entry.name.startswith('.') == False]

    return azure_files + local_files



if __name__ == '__main__':
    data = get_pdf_page_processing_status( 'halftone600dpi', 'masks' )
    data_to_update = data.loc[data.file_available == False].iloc[:25]

    upload_batch(
        data_to_update,
        'masks'
    )
    print( get_batch_files( batch_type='masks' ) )