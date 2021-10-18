import json
import logging
import logging.config
import os
import time
from datetime import datetime
from typing import Any, List

import firebase_admin
from firebase_admin import firestore
from google.cloud import storage
from google.cloud.firestore_v1.base_document import DocumentSnapshot
from google.cloud.firestore_v1.collection import CollectionReference

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
print(log_file_path)
logging.config.fileConfig(fname=log_file_path, disable_existing_loggers=False)

# Get the logger specified in the file
logger = logging.getLogger(__name__)

BUCKET_NAME = os.getenv("BUCKET_NAME")
DEFAULT_BATCH_SIZE = int(os.getenv("DEFAULT_BATCH_SIZE"))
MAX_RUN_TIME = int(os.getenv("MAX_RUN_TIME"))
COLLECTIONS = ['people', 'purchases', 'activationLocation']
OFFSET_COLLECTION = "offset_collection"
OFFSET_COLLECTION_KEY = 'offset'

# Initialize firebase app
firebase_admin.initialize_app()

# Instantiate clients
db = firestore.client()
storage_client = storage.Client()


def get_collection_documents(collection_name: str, query_field: str, query_value: Any, query_sign=">=") -> list:
    """Gets documents from a firebase collection"""
    return db.collection(collection_name).where(query_field, query_sign, query_value).get()


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


def _format_offset_id(collection_name: str) -> str:
    """Takes a collection name and formats it to be used as a document ID"""
    return f"{collection_name}_offset_id"


def batch_upload(bucket_name: str, data: list, collection_name: str):
    filename = _generate_filename(collection_name)
    _write_file(filename, data)
    _upload_blob(bucket_name, filename, f"{collection_name}/{filename}")
    _remove_file(filename)


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
        if len(data) == 0:
            continue
        batch_upload(bucket_name, data, subcollection_name)

    batch_upload(bucket_name, collection_documents, collection_name)


def batch_process(bucket_name: str, collection_name: str, start_time: float):
    offset_dict = get_latest_offset(collection_name)
    if offset_dict:
        offset_key = list(offset_dict.keys())[0]
        offset = offset_dict[offset_key]
    else:
        raise Exception(f'No offset found for collection {collection_name}')

    logger.info(f"Getting documents for collection {collection_name}")
    documents = get_collection_documents(collection_name, offset_key, offset)
    if len(documents) == 0:
        logger.info(f"No more documents to process for collection {collection_name}")
        return

    if (time.time() - start_time >= MAX_RUN_TIME):
        logger.info(f"Job runtime {time.time() - start_time} approaching MAX_RUN_TIME limit")
        return

    process_documents(bucket_name, documents, collection_name)

    logger.info(f"Finished processing documents for collection {collection_name}")
    logger.info(f"Saving offset {offset_key} with offset {offset}...")
    set_latest_offset(collection_name, offset_key, offset)


def get_latest_offset(collection_name: str) -> dict:
    """Fetches the last offset to sync records from that point on"""
    offset_id = _format_offset_id(collection_name)
    doc = db.collection(OFFSET_COLLECTION).document(offset_id).get()
    if doc.exists:
        logger.info(f"Found offset for collection {collection_name}")
        return doc.to_dict()
    else:
        logger.warning(f"No offset found for collection {collection_name} in the {OFFSET_COLLECTION} collection. Using 0 as default offset")
        return None


def set_latest_offset(collection_name: str, offset_key:str, offset: Any):
    """Save the latest offset used"""
    offset_id = _format_offset_id(collection_name)
    data = {offset_key: offset}
    db.collection(OFFSET_COLLECTION).document(offset_id).set(data)


def load_firebase_collections():
    start_time = time.time()
    for collection_name in COLLECTIONS:
        batch_process(BUCKET_NAME, collection_name, start_time)


if __name__ == '__main__':
    load_firebase_collections()
