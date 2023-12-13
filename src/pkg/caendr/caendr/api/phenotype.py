import os

from caendr.services.logger import logger
from sqlalchemy import or_
from flask import request
from datetime import timedelta

from caendr.models.datastore import Species
from caendr.models.error import BadRequestError
from caendr.models.sql import PhenotypeDatabase, PhenotypeMetadata
from caendr.services.cloud.postgresql import db, rollback_on_error


@rollback_on_error
def query_phenotype_metadata(is_bulk_file=False):
    """
      Returns the list of traits with the corresponding metadata.
      By default returns data for non-bulk files
      If 'is_bulk_file' set to True returns traits metadata for Zhang Expression file
    """
    query = PhenotypeMetadata.query

    # Get traits for bulk file
    if is_bulk_file:
        query = query.filter_by(is_bulk_file=True)
    
    # Get traits for non-bulk files
    query = query.filter_by(is_bulk_file=False)

    return query