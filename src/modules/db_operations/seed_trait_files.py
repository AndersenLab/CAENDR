from caendr.services.logger        import logger
from caendr.services.cloud.secret  import get_secret

from caendr.models.datastore       import TraitFile
from caendr.models.error           import NotFoundError, NonUniqueEntity
from caendr.models.status          import PublishStatus
from caendr.services.cloud.sheets  import get_field_from_record
from caendr.utils.data             import unique_id
from caendr.utils.local_files      import LocalGoogleSheet


# Get secret value(s)
ANDERSEN_LAB_TRAIT_SHEET = get_secret(f'ANDERSEN_LAB_TRAIT_SHEET')



def populate_andersenlab_trait_files():
  '''
    Create / update datastore entities for each record in the trait list Google Sheet.
    Assumes the following:
      - `Trait_Name_CaeNDR` column (mapped to `trait_name_caendr` entity field) is unique.
      - A corresponding trait file with the value of the `Trait_Name_CaeNDR` column + `'.tsv'` exists 

    All trait entities populated by this function are listed as belonging to CaeNDR.
  '''
  logger.info(f'Populating datastore phenotype list...')

  # Fetch the Google Sheet and loop through all records
  trait_sheet = LocalGoogleSheet( 'TRAITS', ANDERSEN_LAB_TRAIT_SHEET )
  for record in trait_sheet.fetch_resource().get_all_records():

    # Require that unique CaeNDR trait name is defined
    trait_unique_name = record.get('Trait_Name_CaeNDR')
    if not trait_unique_name:
      continue

    # Look for corresponding trait in datastore
    try:
      tf = TraitFile.query_ds_unique('trait_name_caendr', trait_unique_name, required=True)
      logger.info(f'Updating entry for {trait_unique_name} ({tf.name})...')

    # If doesn't exist yet, create new record entity
    except NotFoundError:
      tf = TraitFile(unique_id())
      logger.info(f'Creating new entry for {trait_unique_name} ({tf.name})...')

    # If unique name is not unique, log the error and continue
    # TODO: Should there be better error-handling here?
    except NonUniqueEntity:
      logger.error(f'Could not uniquely identify trait {trait_unique_name}. Skipping.')
      continue

    # Make updates
    try:
      tf.set_properties(**{

        # Identifying trait
        'filename':          trait_unique_name + '.tsv',
        'trait_name_caendr': trait_unique_name,
        'trait_name_user':   get_field_from_record(record, 'Trait_Name_User'),
        'species':           get_field_from_record(record, 'Species', nullable=False),

        # About trait
        'trait_name_display_1': get_field_from_record(record, 'Trait_Name_Display1'),
        'trait_name_display_2': get_field_from_record(record, 'Trait_Name_Display2'),
        'trait_name_display_3': get_field_from_record(record, 'Trait_Name_Display3'),
        'description_short':    get_field_from_record(record, 'Short_Description'),
        'description_long':     get_field_from_record(record, 'Long_Description'),
        'units':                get_field_from_record(record, 'Units'),

        # Tag list (categories)
        'tags': list(filter(
          lambda v: v is not None,
          [
            get_field_from_record(record, 'Category1'),
            get_field_from_record(record, 'Category2'),
            get_field_from_record(record, 'Category3'),
          ]
        )),

        # Source information
        'publication':       get_field_from_record(record, 'Publication'),
        'protocols':         get_field_from_record(record, 'Protocol'),
        'institution':       get_field_from_record(record, 'Institution'),
        'username':          get_field_from_record(record, 'Captured_By_UserID'),
        'capture_date':      get_field_from_record(record, 'Capture_Date'),

        # CaeNDR lab-specific fields
        # These will not necessarily generalize to other datasets
        'is_bulk_file':      False,
        'dataset':           'caendr',
        'source_lab':        'ECA',
        'publish_status':    PublishStatus.CANONICAL,
      })
      tf.save()

    # Log exception and move onto the next record
    except Exception as ex:
      logger.error(f'Failed to update trait file {trait_unique_name} ({tf.name}): {ex}')
