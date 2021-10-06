import json
import logging
import logging.config
import os
from datetime import datetime
from typing import List

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage
from google.cloud.firestore_v1.base_document import DocumentSnapshot
from google.cloud.firestore_v1.collection import CollectionReference

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
print(log_file_path)
logging.config.fileConfig(fname=log_file_path, disable_existing_loggers=False)

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


def get_subcollection_references(document: DocumentSnapshot) -> CollectionReference:
    """Gets subcollection reference from a document"""

    return document.reference.collections()


def process_subcollection_documents(documents: List[CollectionReference], parent_document_id: str) -> list:
    """Prepare and process documents from a subcollection"""
    subcollections = []
    for document in documents:
        data = {}
        # Add subcollection name
        data['parent_document_id'] = parent_document_id
        data['name'] = document.id

        # Add empty list if not present for subcollection
        if not data.get('data'):
            data['data'] = []

        for sub_document in document.stream():
            data['data'].append({
                    'id': sub_document.id,
                    'data': sub_document.to_dict(),
                })

        subcollections.append(data)

    return subcollections


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


def _generate_filename(collection_name: str) -> str:
    """Generates a filename"""
    return f"collection_{collection_name}_{_get_timestamp_string()}.json"


def _write_file(filename: str, data: list):
    """Writes a json file to local file system"""
    with open(filename, 'w') as f:
        logger.info(f"Writing collection to file {filename}")
        json.dump(data, f)


def _remove_file(filename):
    """Removes file from local filestyem to save space"""
    # If file exists, delete it
    if os.path.isfile(filename):
        os.remove(filename)
        logger.info(f"Removed filename {filename}")
    else:
        logger.warn(f"Warning: {filename} file not found. Could not remove")


def _get_timestamp_string():
    """
    Helper function that generates timestamp string for
    inserting into filename
    """
    return str(datetime.utcnow().timestamp()).replace('.', '_')


def batch_upload(bucket_name: str, data: list, collection_name: str):
    filename = _generate_filename(collection_name)
    _write_file(filename, data)
    # _upload_blob(bucket_name, filename, f"{collection_name}/{filename}")
    # _remove_file(filename)


def process_subcollections(document: DocumentSnapshot) -> list:
    subcollection_references = get_subcollection_references(document)
    return process_subcollection_documents(subcollection_references, document.id)


def process_documents(bucket_name: str, documents: List[DocumentSnapshot], collection_name: str):
    """Prepare and process documents form a collection"""

    collection_documents = []
    subcollection_documents = []
    for document in documents:
        collection_documents.append({
            'id': document.id,
            'data': document.to_dict(),
        })

        subcollections = process_subcollections(document)
        subcollection_documents.extend(subcollections)

    # Splits different types of subcollections into their
    # own file if there is more than one type of collection
    subcollection_set = {col.get('name') for col in subcollection_documents}
    for subcollection_name in subcollection_set:
        data = [col for col in subcollection_documents if col.get('name') == subcollection_name]
        batch_upload(bucket_name, data, subcollection_name)

    batch_upload(bucket_name, collection_documents, collection_name)


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
        docs = get_collection_documents(collection, 3, 500)
        # batch_process(BUCKET_NAME, DEFAULT_BATCH_SIZE, docs, collection)
        process_documents(BUCKET_NAME, docs, collection)


if __name__ == '__main__':
    load_firebase_collections()
