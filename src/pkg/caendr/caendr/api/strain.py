import pandas as pd
import os

from caendr.services.logger import logger
from sqlalchemy import or_
from flask import request
from datetime import timedelta

from caendr.models.datastore import SPECIES_LIST
from caendr.models.error import BadRequestError
from caendr.models.sql import Strain
from caendr.services.cloud.postgresql import db, rollback_on_error
from caendr.services.cloud.storage import get_blob, generate_download_signed_url_v4, download_blob_to_file, upload_blob_from_file, get_google_storage_credentials, generate_blob_url
from caendr.utils.data import unique_id
from caendr.utils.env import get_env_var

MODULE_IMG_THUMB_GEN_SOURCE_PATH = get_env_var('MODULE_IMG_THUMB_GEN_SOURCE_PATH', as_template=True)
MODULE_SITE_BUCKET_PHOTOS_NAME   = get_env_var('MODULE_SITE_BUCKET_PHOTOS_NAME')
MODULE_SITE_BUCKET_PRIVATE_NAME  = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')

BAM_BAI_DOWNLOAD_SCRIPT_NAME     = get_env_var('BAM_BAI_DOWNLOAD_SCRIPT_NAME', as_template=True)
BAM_BAI_PREFIX                   = get_env_var('BAM_BAI_PREFIX', as_template=True)

# TODO: This is still here so functions that haven't been updated will still work.
bam_prefix = 'bam/c_elegans'


#def query_strains(strain_name=None, isotype_name=None, release=None, all_strain_names=False, resolve_isotype=False, issues=False, is_sequenced=False):

@rollback_on_error
def query_strains(
    strain_name:      str  = None,
    isotype_name:     str  = None,
    species:          str  = None,
    release_version        = None,
    all_strain_names: bool = False,
    resolve_isotype:  bool = False,
    issues:           bool = False,
    is_sequenced:     bool = False
  ):
  
  """
      Return the full strain database set

      strain_name - Returns data for only one strain
      isotype_name - Returns data for all strains of an isotype
      release_version - Filters results released prior to release data
      all_strain_names - Return list of all possible strain names (internal use).
      resolve_isotype - Use to search for strains and return their isotype
  """
  query = Strain.query
  
  if release_version:
    query = query.filter(Strain.release <= release_version)

  if strain_name or resolve_isotype:
    query = query.filter(
      or_(
        Strain.previous_names.like(f"%{strain_name},%"),
        Strain.previous_names.like(f"%,{strain_name},"),
        Strain.previous_names.like(f"%{strain_name}"),
        Strain.previous_names == strain_name,
        Strain.strain == strain_name
      )
    ).first()

  elif isotype_name:
    query = query.filter(Strain.isotype == isotype_name)

  else:
    query = query

  if species is not None:
    if species in SPECIES_LIST.keys():
      query = query.filter(Strain.species_name == species)
    else:
      raise BadRequestError(f'Unrecognized species ID "{species}".')

  if is_sequenced is True:
    query = query.filter(Strain.sequenced == True)

  if issues is False:
    query = query.filter(Strain.issues == False)
    query = query.filter(Strain.isotype != None)
    query = query.all()
  else:
    query = query.all()

  if all_strain_names:
    previous_strain_names = sum([x.previous_names.split(",") for x in query if x.previous_names], [])
    results = [x.strain for x in query] + previous_strain_names
    return results

  if resolve_isotype:
    if query:
      # LSJ1/LSJ2 prev. N2; So N2 needs to be specific.
      if strain_name == 'N2':
        return 'N2'
      return query.isotype
      
  
  return query


@rollback_on_error
def get_strains(known_origin=False, issues=False):
  """
    Returns a list of strains;

    Represents all strains

    Args:
        known_origin: Returns only strains with a known origin
        issues: Return only strains without issues
  """
  ref_strain_list = Strain.query.filter(Strain.isotype_ref_strain == True).all()
  ref_strain_list = {x.isotype: x.strain for x in ref_strain_list}
  result = Strain.query
  if known_origin or 'origin' in request.path:
    result = result.filter(Strain.latitude != None)

  if issues is False:
    result = result.filter(Strain.isotype != None)
    result = result.filter(Strain.issues == False)

  result = result.all()
  for strain in result:
    # Set an attribute for the reference strain of every strain
    strain.reference_strain = ref_strain_list.get(strain.isotype, None)
  return result


@rollback_on_error
def get_strain_sets():
  # TODO: change this to a sqlalchemy query instead
  df = pd.read_sql_table(Strain.__tablename__, db.engine)
  result = df[['strain_set', 'species_name', 'strain', 'isotype' ]].dropna(how='any') \
                                        .groupby(['strain_set', 'species_name'])['strain'] \
                                        .apply(list) \
                                        .to_dict()  
  return result


def get_strain_img_url(strain_name, species, thumbnail=True):
  ''' Returns a list of public urls for images of the isotype in cloud storage '''

  path = MODULE_IMG_THUMB_GEN_SOURCE_PATH.get_string(**{
    'SPECIES': species,
  })

  blob = get_blob(MODULE_SITE_BUCKET_PHOTOS_NAME, f"{path}/{strain_name}.jpg")
  if blob and thumbnail:
    blob = get_blob(MODULE_SITE_BUCKET_PHOTOS_NAME, f"{path}/{strain_name}.thumb.jpg")

  try:
    return blob.public_url
  except AttributeError:
    return None


def get_bam_bai_download_link(species, strain_name, ext, signed=False):
  '''
    Get the URL to download a BAM or BAI file for a given strain.

    Args:
      species: The Species object that this strain is under
      strain_name: The name of the strain to download
      ext: The extension of the desired file. Should be either 'bam' or 'bam.bai'.
      signed (bool): Whether the generated URL should be signed. Defaults to False.
  '''

  bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  bam_prefix = BAM_BAI_PREFIX.get_string(SPECIES=species.name)

  blob_name = f'{bam_prefix}/{strain_name}.{ext}'

  if signed:
    return generate_download_signed_url_v4(bucket_name, blob_name)
  else:
    return generate_blob_url(bucket_name, blob_name)


# TODO: This is now out of date, since script name relies on species & release
def fetch_bam_bai_download_script(reload=False):
  if reload and os.path.exists(BAM_BAI_DOWNLOAD_SCRIPT_NAME):
    os.remove(BAM_BAI_DOWNLOAD_SCRIPT_NAME)
    
  if not os.path.exists(BAM_BAI_DOWNLOAD_SCRIPT_NAME):
    bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
    blob_name = f'{bam_prefix}/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}'
    logger.debug('Reloading bam/bai download script from: bucket:{bucket_name} blob:{blob_name}')
    return download_blob_to_file(bucket_name, blob_name, BAM_BAI_DOWNLOAD_SCRIPT_NAME)

  return BAM_BAI_DOWNLOAD_SCRIPT_NAME


def generate_bam_bai_download_script(species, release, signed=False):
  '''
    Generate a Bash script that downloads all BAM/BAI files for a given species and release.

    Args:
      species: The Species object to download from.
      release: The DatasetRelease object to download from.
      signed (bool): Whether the generated URLs should be signed. Defaults to False.

    Return:
      Generator that yields the file line by line.
  '''

  expiration  = timedelta(days=7)
  bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  credentials = get_google_storage_credentials()

  # Get the location of the BAM files in the bucket for this species/release
  bam_prefix = BAM_BAI_PREFIX.get_string(**{
    'SPECIES': species.name,
    'RELEASE': release.version,
  })

  # Get a list of all strains for this species
  strain_listing = query_strains(is_sequenced=True, species=species.name)

  # Log species and release
  yield f'# Species: { species.short_name }\n'
  yield f'# Release: { release.version }\n'
  yield '\n\n'

  # Add download statements for each strain
  for strain in strain_listing:
    yield f'# Strain: {strain}\n'
    bam_path = f'{bam_prefix}/{strain}.bam'
    bai_path = f'{bam_prefix}/{strain}.bam.bai'

    # Generate download URLs
    if signed:
      bam_url = generate_download_signed_url_v4(bucket_name, bam_path, expiration=expiration, credentials=credentials)
      bai_url = generate_download_signed_url_v4(bucket_name, bai_path, expiration=expiration, credentials=credentials)
    else:
      bam_url = generate_blob_url(bucket_name, bam_path)
      bai_url = generate_blob_url(bucket_name, bai_path)

    # Add download statements
    if bam_url:
      yield f'wget -O "{strain}.bam" "{bam_url}"\n'
    if bai_url:
      yield f'wget -O "{strain}.bam.bai" "{bai_url}"\n'
    yield '\n'


# NOTE: This is likely obsolete
def upload_bam_bai_download_script(species, release, signed=False):
  '''
    Generate the download script for a given species & release, and upload it to the datastore.
  '''

  filename = BAM_BAI_DOWNLOAD_SCRIPT_NAME.get_string(**{
    'SPECIES': species.name,
    'RELEASE': release.version,
  })

  bam_prefix = BAM_BAI_PREFIX.get_string(**{
    'SPECIES': species.name,
    'RELEASE': release.version,
  })

  bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  blob_name = f'{bam_prefix}/{filename}'

  # Generate a unique local filename
  local_filename = f'{unique_id()}-{filename}'

  # If somehow this already exists, raise an error
  if os.path.exists(local_filename):
    raise Exception(f'Couldn\'t generate and upload BAM/BAI download script: local filename "{local_filename}" already exists')

  # Try to generate and upload the file
  try:
    with open(local_filename, 'a') as f:
      for line in generate_bam_bai_download_script(species, release, signed=signed):
        f.write(line)
    upload_blob_from_file(bucket_name, local_filename, blob_name)

  # Make sure the local file is removed before returning
  finally:
    try:
      os.remove(local_filename)
    except FileNotFoundError:
      pass
