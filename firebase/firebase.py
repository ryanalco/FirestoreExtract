import json
import logging
import logging.config
import os
from typing import List

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage
from google.cloud.firestore_v1.base_document import DocumentSnapshot
from google.cloud.firestore_v1.collection import CollectionReference

logging.config.fileConfig(fname='logging.conf', disable_existing_loggers=False)

# Get the logger specified in the file
logger = logging.getLogger(__name__)

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


def get_collection_documents(collection_name: str, batch_size: int, offset: int) -> list:
    """Gets documents from a firebase collection"""
    return db.collection(collection_name).limit(batch_size).offset(offset).get()


def get_subcollection_documents(document: DocumentSnapshot) -> CollectionReference:
    """Gets subcollection reference from a document"""

    data = {'parent_document_id': document.id, 'subcollection': {}}
    return document.reference.collections()
    for collection_reference in subcollection:
        data['subcollection']['name'] = collection_reference.id

        if not data['subcollection'].get('data'):
            data['subcollection']['data'] = []

        for sub_document in collection_reference.stream():
            data['subcollection']['data'].append({
                    'id': sub_document.id,
                    'data': sub_document.to_dict(),
                })

    return data

def json_serialize_subcollection_documents(documents: List[CollectionReference],
                                           parent_document_id: str) -> list:
    data = {'parent_document_id': parent_document_id, 'subcollection': {}}
    for document in documents:
        data['subcollection']['name'] = document.id

        if not data['subcollection'].get('data'):
            data['subcollection']['data'] = []

        for sub_document in document.stream():
            data['subcollection']['data'].append({
                    'id': sub_document.id,
                    'data': sub_document.to_dict(),
                })


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

    logger.info(f"File {source_file_name} uploaded to {destination_blob_name}.")


def _write_file(data: list, collection_name: str, batch_num: int) -> str:
    """Writes a json file to local file system"""
    filename = f"collection_{collection_name}_{batch_num}.json"
    with open(filename, 'w') as f:
        logger.info(f"Writing collection {collection_name} - batch {batch_num} to file {filename}")
        json.dump(data, f)

    return filename


def _remove_file(filename):
    """Removes file from local filestyem to save space"""
    # If file exists, delete it
    if os.path.isfile(filename):
        os.remove(filename)
        logger.info(f"Removed filename {filename}")
    else:
        logger.warn(f"Warning: {filename} file not found. Could not remove")


def batch_upload(bucket_name: str, data: list, collection_name: str, batch_num: int):
    filename = _write_file(data, collection_name, batch_num)
    _upload_blob(bucket_name, filename, filename)
    _remove_file(filename)


def batch_process(bucket_name: str, batch_size: int, docs: list, collection_name: str):
    batch_num = 0
    current_size = 0
    batch = []

    for doc in docs:
        batch.append({
            'id': doc.id,
            'data': doc.to_dict(),
        })

        # If batch list equals batch size, write batch to file,
        # clear the batch list, and reset counters
        if current_size == batch_size:
            batch_upload(bucket_name, batch, collection_name, batch_num)
            batch = []
            current_size = 0
            batch_num += 1
            break
            # continue

        current_size += 1

    # If documents remain in batch, write to file
    if len(batch) != 0:
        batch_upload(bucket_name, batch, collection_name, batch_num)


def load_firebase_collections():
    for collection in COLLECTIONS:
        logger.info(f"Getting documents for collection: {collection}...")
        docs = get_collection_documents(collection)
        batch_process(BUCKET_NAME, DEFAULT_BATCH_SIZE, docs, collection)


if __name__ == '__main__':
    load_firebase_collections()
