import pandas as pd
import os

from caendr.services.logger import logger
from sqlalchemy import or_
from flask import request
from datetime import timedelta

from caendr.models.datastore import SPECIES_LIST
from caendr.models.error import BadRequestError
from caendr.models.sql import Strain
from caendr.services.cloud.postgresql import db
from caendr.services.cloud.storage import get_blob, generate_download_signed_url_v4, download_blob_to_file, upload_blob_from_file, get_google_storage_credentials

MODULE_IMG_THUMB_GEN_SOURCE_PATH = os.environ.get('MODULE_IMG_THUMB_GEN_SOURCE_PATH')
MODULE_SITE_BUCKET_PHOTOS_NAME = os.environ.get('MODULE_SITE_BUCKET_PHOTOS_NAME')
MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')

BAM_BAI_DOWNLOAD_SCRIPT_NAME = "bam_bai_signed_download_script.sh"
bam_prefix = 'bam/c_elegans'


#def query_strains(strain_name=None, isotype_name=None, release=None, all_strain_names=False, resolve_isotype=False, issues=False, is_sequenced=False):

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


def get_strain_sets():
  # TODO: change this to a sqlalchemy query instead
  df = pd.read_sql_table(Strain.__tablename__, db.engine)
  result = df[['strain_set', 'species_name', 'strain', 'isotype' ]].dropna(how='any') \
                                        .groupby(['strain_set', 'species_name'])['strain'] \
                                        .apply(list) \
                                        .to_dict()  
  return result


def get_strain_img_url(strain_name, thumbnail=True):
  ''' Returns a list of public urls for images of the isotype in cloud storage '''
  blob = get_blob(MODULE_SITE_BUCKET_PHOTOS_NAME, f"{MODULE_IMG_THUMB_GEN_SOURCE_PATH}/{strain_name}.jpg")
  if blob and thumbnail:
    blob = get_blob(MODULE_SITE_BUCKET_PHOTOS_NAME, f"{MODULE_IMG_THUMB_GEN_SOURCE_PATH}/{strain_name}.thumb.jpg")

  try:
    return blob.public_url
  except AttributeError:
    return None
  
  
def get_bam_bai_download_link(strain_name, ext):
  blob_name = f'{bam_prefix}/{strain_name}.{ext}'
  bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  return generate_download_signed_url_v4(bucket_name, blob_name)


def fetch_bam_bai_download_script(reload=False):
  if reload and os.path.exists(BAM_BAI_DOWNLOAD_SCRIPT_NAME):
    os.remove(BAM_BAI_DOWNLOAD_SCRIPT_NAME)
    
  if not os.path.exists(BAM_BAI_DOWNLOAD_SCRIPT_NAME):
    bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
    blob_name = f'{bam_prefix}/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}'
    logger.debug('Reloading bam/bai download script from: bucket:{bucket_name} blob:{blob_name}')
    return download_blob_to_file(bucket_name, blob_name, BAM_BAI_DOWNLOAD_SCRIPT_NAME)

  return BAM_BAI_DOWNLOAD_SCRIPT_NAME


def get_joined_strain_list():
  strain_listing = query_strains(is_sequenced=True)
  joined_strain_list = ''
  for strain in strain_listing:
    joined_strain_list += strain.strain + ','
  return joined_strain_list


def generate_bam_bai_download_script(joined_strain_list):
  expiration = timedelta(days=7)
  filename = BAM_BAI_DOWNLOAD_SCRIPT_NAME
  blob_name = f'{bam_prefix}/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}'
  bucket_name = MODULE_SITE_BUCKET_PRIVATE_NAME
  credentials = get_google_storage_credentials()
  
  if os.path.exists(filename):
    os.remove(filename)
  f = open(filename, "a")

  strain_listing = joined_strain_list.split(',')
  for strain in strain_listing:
    f.write(f'\n\n# Strain: {strain}')
    bam_path = f'{bam_prefix}/{strain}.bam'
    bai_path = f'{bam_prefix}/{strain}.bam.bai'
    bam_signed_url = generate_download_signed_url_v4(bucket_name, bam_path, expiration=expiration, credentials=credentials)
    bai_signed_url = generate_download_signed_url_v4(bucket_name, bai_path, expiration=expiration, credentials=credentials)
    if bam_signed_url:
      f.write(f'\nwget -O "{strain}.bam" "{bam_signed_url}"')
    if bai_signed_url:
      f.write(f'\nwget -O "{strain}.bam.bai" "{bai_signed_url}"')

  f.close()
  upload_blob_from_file(bucket_name, filename, blob_name)

