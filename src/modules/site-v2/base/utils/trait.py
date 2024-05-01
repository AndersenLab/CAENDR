import bleach
import csv

from caendr.models.error              import FileUploadError
from caendr.models.datastore          import TraitFile, Species
from caendr.models.status             import PublishStatus
from caendr.models.sql                import PhenotypeMetadata, PhenotypeDatabase
from caendr.services.cloud.storage    import upload_blob_from_file_object, check_blob_exists, get_blob_if_exists
from caendr.services.cloud.postgresql import rollback_on_error_handler
from caendr.services.logger           import logger
from caendr.services.validate         import validate_file, StrainValidator, NumberValidator
from caendr.services.cloud.datastore  import delete_ds_entity_by_ref
from caendr.api.phenotype             import get_trait
from caendr.utils.data                import unique_id
from caendr.utils.env                 import get_env_var
from caendr.utils.local_files         import LocalUploadFile
from constants                        import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS

MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
MODULE_DB_OPERATIONS_TRAITFILE_PUBLIC_FILEPATH = get_env_var('MODULE_DB_OPERATIONS_TRAITFILE_PUBLIC_FILEPATH')


def add_trait(form_data, user):
  """ 
    Add a trait to the database by permoforming the following operations:
        1. Create a new TraitFile object with the user submitted data and save it to Datastore.
        2. Seed the trait data to Phenotype Metadata SQL table.
        3. Save the file to GCP bucket.
        4. Parse and seed the file data to Phenotype Database SQL table.
    On the failure of any of the above operations rolls back to the initial state and returns an error message.
  """
  try:
    # Create a new TraitFile oject
    tf = TraitFile(unique_id())

    # Create a unique filename for file uload
    hashed_filename = f'{unique_id()}.tsv'  
    tf.set_properties(**{
      # User submitted data
      'trait_name_user':      bleach.clean(form_data.trait_name_user.data),
      'trait_name_display_1': bleach.clean(form_data.trait_name_display_1.data),
      'trait_name_display_2': bleach.clean(form_data.trait_name_display_2.data),
      'trait_name_display_3': bleach.clean(form_data.trait_name_display_2.data),
      'filename':             bleach.clean(form_data.file.data.filename),
      'species':              bleach.clean(form_data.species.data),
      'description_short':    bleach.clean(form_data.description_short.data),
      'description_long':     bleach.clean(form_data.description_long.data),
      'units':                bleach.clean(form_data.units.data),
      'tags':                 [ bleach.clean(tag) for tag in form_data.tags.data ],
      'institution':          bleach.clean(form_data.institution.data),
      'source_lab':           bleach.clean(form_data.source_lab.data),
      'protocols':            bleach.clean(form_data.protocols.data),        
      'publication':          bleach.clean(form_data.publication.data),
  
      # Internally used data
      'dataset':           'public',
      'publish_status':    PublishStatus.UPLOADED,
      'is_bulk_file':      False,
      'hashed_filename':   hashed_filename,
    })

    tf.set_user(user)

    # Save te TraitFile object to Datastore
    tf.save()
  except Exception as ex:
    logger.error(f'Failed to create a trait file {form_data.trait_name_user.data}: {ex}')
    return {'message': 'Failed to submit a form. Please try again later.'}, 500
  
  try:
    # Seed to Phenotype Metadata SQL table
    with rollback_on_error_handler():
      new_trait = PhenotypeMetadata()
      new_trait.add(tf)
  except Exception as ex:
    rollback_submission_on_error(tf.name)
    logger.error(f'Failed to seed the trait to the database: {ex}')
    return {'message': 'Failed to submit a form. Please try again later.'}, 500
      
  # Save file to GCP bucket
  species_name = Species.get(form_data.species.data).name
  blob_name = f'{MODULE_DB_OPERATIONS_TRAITFILE_PUBLIC_FILEPATH}/{species_name}/{user.name}/{hashed_filename}'

  # Check if the file already exists
  if check_blob_exists(MODULE_DB_OPERATIONS_BUCKET_NAME, blob_name):
    return {'message': 'File already exists.'}, 400
  else:
    upload_blob_from_file_object(MODULE_DB_OPERATIONS_BUCKET_NAME, form_data.file.data, blob_name)

  # Reset the file pointer
  form_data.file.data.seek(0)
      
  try:
    # Seed the file data to Phenotype Database SQL table
    with LocalUploadFile(form_data.file.data, valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS) as file:
     # Validate the file
      try:
        validate_file(file, [
                              StrainValidator( 'strain', species=tf['species'], force_unique=True, force_unique_msgs={} ),
                              NumberValidator( None, accept_float=True, accept_na=True ),
                            ])
      except Exception as ex:
        rollback_submission_on_error(tf.name, blob_name)
        logger.error(f'Failed to validate the file: {ex.msg}')
        return {'message': f'Failed to validate the file: {ex.msg}'}, 400
      
      # Parse the trait file
      trait_data_list = []
      with open(file) as f:
        for idx, row in enumerate( csv.reader(f, delimiter='\t') ):
          if idx == 0:
            continue
          else:
            trait_data = {
              'trait_name':  tf['trait_name_user'],
              'strain_name': row[0],
              'trait_value': row[1],
              'metadata_id': tf.name
            }
            trait_data_list.append(trait_data)
      try:
        with rollback_on_error_handler():
          trait_data = PhenotypeDatabase()
          trait_data.add_trait_data('hello')
      except Exception as ex:
        rollback_submission_on_error(tf.name, blob_name)
        logger.error(f'Failed to seed the file data to the database: {ex}')

  except FileUploadError as ex:
    rollback_submission_on_error(tf.name, blob_name)
    logger.error(f'Failed to upload a file {form_data.file.data.filename}: {ex}')
    return {'message': 'Failed to submit a form. Please try again later.'}, 500
  
  return {'message': 'Trait submitted successfully.'}, 200


def rollback_submission_on_error(trait_id, blob_name=None):
    """
      Rollback the trait submission on error by performing the following operations:
          1. Delete the TraitFile object from Datastore.
          2. Delete the trait from Phenotype Metadata SQL table.
          3. Delete the file from GCP bucket.
          4. Delete the file data from Phenotype Database SQL table.
    """
    tf = TraitFile.get_ds(trait_id)
    if tf is None:
      logger.error(f'Failed to retrieve the trait file {trait_id}')
      return

    # Delete the previousely created TraitFile object
    delete_ds_entity_by_ref(TraitFile.kind, tf.name)

    # Delete a new trait from Phenotype Metadata SQL table
    trait = get_trait(tf.name)
    if trait:
      trait.delete()

    # Delete the file from GCP bucket
    if blob_name:
      blob = get_blob_if_exists(MODULE_DB_OPERATIONS_BUCKET_NAME, blob_name)
      if blob:
        blob.delete()
      
    # Delete the file data from Phenotype Database SQL table
    PhenotypeDatabase.delete_by_metadata_id(tf.name)
      
