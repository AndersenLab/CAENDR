from logzero import logger
from google.cloud import storage
import os
from caendr.models.datastore.entity import Entity

client = storage.Client()

ETL_LOGS_BUCKET_NAME = os.getenv('ETL_LOGS_BUCKET_NAME', None)
if ETL_LOGS_BUCKET_NAME is None:
    raise "E_MISSING_ETL_LOG_BUCKET_NAME"

def is_valid_entity_id(entity_id):
    return entity_id is not None and entity_id.isalnum()


class PersistentLogger():
    def __init__(self, service_name):
        self.service_name = service_name

    def log(self, operation_id, message):
        if not is_valid_entity_id(operation_id):
            logger.warning(f"Invalid to update database_operation with id: {operation_id}")
            return

        bucket = client.get_bucket(ETL_LOGS_BUCKET_NAME)
        filepath = f"logs/{self.service_name}/{operation_id}/output"
        uri = f"gs://{ETL_LOGS_BUCKET_NAME}/{filepath}"

        CRLF = "\n"
        blob = bucket.get_blob(filepath)
        if blob is not None:
            old_content = blob.download_as_string()
            new_content = f"{old_content}{CRLF}{message}"
        else:
            blob = storage.Blob(filepath, bucket)
            new_content = f"{message}"

        blob.upload_from_string(new_content)

        # update datastore operation object (get or create)
        op = Entity(operation_id)
        logger.info(f"Appending logs to database_operation - {op.id}")
        op.set_properties(logs=uri)
        op.save()

    def get(self, operation_id):
        if not is_valid_entity_id(operation_id):
            logger.warning(f"Invalid to update database_operation with id: {operation_id}")
            return ""

        try:
            bucket = client.get_bucket(ETL_LOGS_BUCKET_NAME)
            filepath = f"logs/{self.service_name}/{operation_id}/output"
            uri = f"gs://{ETL_LOGS_BUCKET_NAME}/{filepath}"

            CRLF = "\n"
            blob = bucket.get_blob(filepath)
            if blob is None:
                return ""
            content = blob.download_as_string()
            return content
        except:
            return ""

