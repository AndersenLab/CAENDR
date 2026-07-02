import pandas as pd
import os
from numpy import int16

from caendr.services.logger import logger
from sqlalchemy import or_, select
from flask import request

from caendr.models.datastore import Species
from caendr.models.error import BadRequestError
from caendr.models.sql import Strain
from caendr.services.cloud.postgresql import db, rollback_on_error
from caendr.services.cloud.storage import get_blob, download_blob_to_file, upload_blob_from_file
from caendr.services.cloud.aws_storage import aws_generate_blob_uri, AWSBlobURISchema
from caendr.utils.data import unique_id
from caendr.utils.env import get_env_var

MODULE_IMG_THUMB_GEN_SOURCE_PATH = get_env_var('MODULE_IMG_THUMB_GEN_SOURCE_PATH', as_template=True)
MODULE_SITE_BUCKET_PHOTOS_NAME   = get_env_var('MODULE_SITE_BUCKET_PHOTOS_NAME')
MODULE_SITE_BUCKET_PRIVATE_NAME  = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')
AWS_OPEN_DATA_BUCKET             = get_env_var('AWS_OPEN_DATA_BUCKET')

BAM_BAI_DOWNLOAD_SCRIPT_NAME     = get_env_var('BAM_BAI_DOWNLOAD_SCRIPT_NAME', as_template=True)
BAM_BAI_PREFIX                   = get_env_var('BAM_BAI_PREFIX', as_template=True)
VCF_TBI_PREFIX                   = get_env_var('VCF_TBI_PREFIX', as_template=True)
GVCF_PREFIX                      = get_env_var('GVCF_PREFIX', as_template=True)
PREFICES = {"bam": BAM_BAI_PREFIX, "bam.bai": BAM_BAI_PREFIX, "vcf.gz": VCF_TBI_PREFIX, "vcf.gz.tbi": VCF_TBI_PREFIX, "g.vcf.gz": GVCF_PREFIX}

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
  stmt = select(Strain)

  if release_version:
    stmt = stmt.where(Strain.release <= release_version)

  # If searching for a specific strain name, return a single result
  if strain_name or resolve_isotype:
    if resolve_isotype and not strain_name:
      return None

    stmt_specific = stmt.where(
      or_(
        Strain.previous_names.like(f"%{strain_name},%"),
        Strain.previous_names.like(f"%,{strain_name},"),
        Strain.previous_names.like(f"%{strain_name}"),
        Strain.previous_names == strain_name,
        Strain.strain == strain_name
      )
    )
    result_obj = db.session.execute(stmt_specific).scalars().first()

    if resolve_isotype:
      if result_obj:
        # LSJ1/LSJ2 prev. N2; So N2 needs to be specific.
        if strain_name == 'N2':
          return 'N2'
        return result_obj.isotype
      return None

    return result_obj

  # Otherwise build the full-list statement
  if isotype_name:
    stmt = stmt.where(Strain.isotype == isotype_name)

  if species is not None:
    if species in Species.all().keys():
      stmt = stmt.where(Strain.species_name == species)
    else:
      raise BadRequestError(f'Unrecognized species ID "{species}".')

  if is_sequenced is True:
    stmt = stmt.where(Strain.sequenced == True)

  if issues is False:
    stmt = stmt.where(Strain.issues == False)
    stmt = stmt.where(Strain.isotype != None)

  results = db.session.execute(stmt).scalars().all()

  if all_strain_names:
    previous_strain_names = sum([x.previous_names.split(",") for x in results if x.previous_names], [])
    results = [x.strain for x in results] + previous_strain_names
    return results

  return results


@rollback_on_error
def get_strains(known_origin=False, issues=False, distributed_only=False):
  """
    Returns a list of strains;

    Represents all strains

    Args:
        known_origin: Returns only strains with a known origin
        issues: Return only strains without issues
  """
  ref_strain_list = db.session.execute(
    select(Strain).where(Strain.isotype_ref_strain == True)
  ).scalars().all()

  ref_strain_list = {x.isotype: x.strain for x in ref_strain_list}
  result = select(Strain)
  if known_origin or 'origin' in request.path:
    result = result.where(Strain.latitude != None)

  if issues is False:
    result = result.where(Strain.isotype != None)
    result = result.where(Strain.issues == False)

  if distributed_only is True:
    result = result.where(Strain.distribute == True)

  result = db.session.execute(result).scalars().all()
  for strain in result:
    # Set an attribute for the reference strain of every strain
    strain.reference_strain = ref_strain_list.get(strain.isotype, None)
  result = sorted(result, key=lambda x: (x.species, x.to_sortable_isotype(x), x.to_sortable_strain(x)))
  return result


@rollback_on_error
def get_strain_index_dict():
  """
  Returns a dict of strains and their indices
  """
  stmt = select(Strain)
  stmt = stmt.where(Strain.sequenced == True)
  result = db.session.execute(stmt.order_by(Strain.strain)).scalars().all()
  strain_indices = {strain.strain: i & 0xFFFF for i, strain in enumerate(result)}
  return strain_indices


@rollback_on_error
def get_index_strain_dict():
  """
  Returns a dict of strains and their indices
  """
  stmt = select(Strain)
  stmt = stmt.where(Strain.sequenced == True)
  result = db.session.execute(stmt.order_by(Strain.strain)).scalars().all()
  strain_indices = {i & 0xFFFF: strain.strain for i, strain in enumerate(result)}
  return strain_indices


@rollback_on_error
def get_strain_sets():
  # TODO: change this to a sqlalchemy query instead
  rows = db.session.execute(
      select(
          Strain.strain_set,
          Strain.species_name,
          Strain.strain,
          Strain.isotype,
      )
      .where(Strain.strain_set.isnot(None))
      .where(Strain.species_name.isnot(None))
  ).all()

  grouped = {}
  for strain_set, species_name, strain, isotype in rows:
    if strain is None or isotype is None:
      continue
    grouped.setdefault((strain_set, species_name), []).append(strain)
  return grouped


def get_strain_img_url(strain_name, species, thumbnail=True):
  ''' Returns a list of public urls for images of the isotype in cloud storage '''

  path = MODULE_IMG_THUMB_GEN_SOURCE_PATH.get_string(**{
    'SPECIES': species,
  })

  blob = get_blob(MODULE_SITE_BUCKET_PHOTOS_NAME, f"{path}/{strain_name}.jpg")
  if thumbnail and blob:
    thumb = get_blob(MODULE_SITE_BUCKET_PHOTOS_NAME, f"{path}/{strain_name}.thumb.jpg")
    if thumb:
      blob = thumb

  try:
    return blob.public_url
  except AttributeError:
    return None


def get_bam_bai_vcf_download_link(species, strain_name, ext, signed=False):
  '''
    Get the URL to download a BAM, BAI, VCF, TBI, or gVCF file for a given strain.

    Args:
      species: The Species object that this strain is under
      strain_name: The name of the strain to download
      ext: The extension of the desired file. Should be either 'bam', 'bam.bai', 'vcf.gz', 'vcf.gz.tbi', or 'g.vcf.gz'
      signed (bool): Whether the generated URL should be signed. Defaults to False.
  '''

  if ext not in PREFICES:
    raise ValueError(f'Unsupported file extension: {ext}')

  bucket_name = AWS_OPEN_DATA_BUCKET
  file_prefix  = PREFICES[ext].get_string(SPECIES=species.name)

  return aws_generate_blob_uri( bucket_name, file_prefix, f'{strain_name}.{ext}', schema=AWSBlobURISchema.HTTPS )

# Is this deprecated?
def fetch_bam_bai_download_script(species, release, reload=False):

  bucket_name = AWS_OPEN_DATA_BUCKET
  bam_prefix  = BAM_BAI_PREFIX.get_string(**{
    'SPECIES': species.name,
    'RELEASE': release.version,
  })
  script_name = BAM_BAI_DOWNLOAD_SCRIPT_NAME.get_string(**{
    'SPECIES': species.name,
    'RELEASE': release.version,
  })

  if reload and os.path.exists(script_name):
    os.remove(script_name)

  if not os.path.exists(script_name):
    logger.debug(f'Reloading bam/bai download script from: bucket:{bucket_name} path:{bam_prefix}/{script_name}')
    return download_blob_to_file(bucket_name, bam_prefix, script_name)

  return script_name


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

  bucket_name = AWS_OPEN_DATA_BUCKET

  # Package keyword args for signing URLs into a dict
  sign_dict = {
    'schema':      AWSBlobURISchema.HTTPS,
  #   'expiration':  timedelta(days=7),
  #   'credentials': get_google_storage_credentials(),
  }

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

    # Generate filenames
    bam_fname = f'{strain}.bam'
    bai_fname = f'{strain}.bam.bai'

    # Generate download URLs
    bam_url = aws_generate_blob_uri(bucket_name, bam_prefix, bam_fname, **sign_dict)
    bai_url = aws_generate_blob_uri(bucket_name, bam_prefix, bai_fname, **sign_dict)

    # Add download statements
    if bam_url:
      yield f'wget -O "{bam_fname}" "{bam_url}"\n'
    if bai_url:
      yield f'wget -O "{bai_fname}" "{bai_url}"\n'
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



