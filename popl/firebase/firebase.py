import json
import os

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage

POPL_SERVICE_ACCOUNT_PATH = os.getenv("POPL_SERVICE_ACCOUNT_PATH")
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH")
BUCKET_NAME = os.getenv("BUCKET_NAME")
DEFAULT_BATCH_SIZE = 100
COLLECTIONS = ['people']

# Get credentials
cred = credentials.Certificate(POPL_SERVICE_ACCOUNT_PATH)
firebase_admin.initialize_app(cred)

# Instantiate clients
db = firestore.client()
storage_client = storage.Client.from_service_account_json(json_credentials_path=SERVICE_ACCOUNT_PATH)


def get_collection_documents(collection_name: str) -> list:
    """Gets all documents from a firebase collection"""
    return db.collection(collection_name).stream()


def _upload_blob(bucket_name: str, source_file_name: str, destination_blob_name: str):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    # storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(f"File {source_file_name} uploaded to {destination_blob_name}.")


def _write_file(data: list, collection_name: str, batch_num: int) -> str:
    """Writes a json file to local file system"""
    filename = f"collection_{collection_name}_{batch_num}.json"
    with open(filename, 'w') as f:
        print(f"Writing collection {collection_name} - batch {batch_num} to file {filename}")
        json.dump(data, f)

    return filename


def _remove_file(filename):
    """Removes file from local filestyem to save space"""
    # If file exists, delete it
    if os.path.isfile(filename):
        os.remove(filename)
        print(f"Removed filename {filename}")
    else:
        print(f"Warning: {filename} file not found. Could not remove")


def batch_upload(bucket_name: str, data: list, collection_name: str, batch_num: int):
    filename = _write_file(data, collection_name, batch_num)
    _upload_blob(bucket_name, filename, filename)
    _remove_file(filename)


def batch_process(bucket_name: str, batch_size: int, docs: list, collection_name: str):
    batch_num = 0
    current_size = 0
    batch = []

    for doc in docs:
        batch.append(doc.to_dict())

        # If batch list equals batch size, write batch to file,
        # clear the batch list, and reset counters
        if current_size == batch_size:
            batch_upload(bucket_name, batch, collection_name, batch_num)
            batch = []
            current_size = 0
            batch_num += 1
            continue

        current_size += 1

    # If documents remain in batch, write to file
    if len(batch) != 0:
        batch_upload(bucket_name, batch, collection_name, batch_num)


def main():
    for collection in COLLECTIONS:
        docs = get_collection_documents(collection)
        batch_process(BUCKET_NAME, DEFAULT_BATCH_SIZE, docs, collection)


if __name__ == '__main__':
    main()
