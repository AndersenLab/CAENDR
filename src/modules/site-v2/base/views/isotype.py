from caendr.services.logger import logger

from extensions import cache, compress
from flask import render_template, request, url_for, redirect, Blueprint, abort, flash, jsonify

from caendr.api.strain import query_strains, get_strain_img_url
from caendr.utils.json import dump_json
from caendr.utils.env import get_env_var
from caendr.models.sql import Strain
from caendr.services.cloud.storage import get_blob_list


MODULE_SITE_BUCKET_PHOTOS_NAME   = get_env_var('MODULE_SITE_BUCKET_PHOTOS_NAME')




isotype_bp = Blueprint(
  'isotype', __name__, template_folder='templates'
)



#
# Base View
#

@isotype_bp.route('/')
@cache.memoize(60*60)
def isotype():
  """
    Required root endpoint.
  """
  abort(404)



#
# Isotype View
#

@isotype_bp.route('/<isotype_name>/')
@isotype_bp.route('/<isotype_name>/<release>')
@cache.memoize(60*60)
def isotype_page(isotype_name, release=None):
  """
    Isotype page
  """

  # Get the list of strains for this isotype, throwing the appropriate error if this fails
  try:
    isotype_strains = query_strains(isotype_name=isotype_name)
  except Exception as ex:
    logger.error(f'Failed to retrieve strain list for isotype {isotype_name}: {ex}')
    abort(500)
  if not isotype_strains:
    abort(404)

  # Try to sort the list of strains
  # If this fails for any reason, we can keep going with the unsorted list
  try:
    isotype_strains = Strain.sort_by_strain( isotype_strains )
  except Exception as ex:
    logger.error(f'Failed to sort strain list for isotype {isotype_name}: {ex}')

  try:
    species = isotype_strains[0].species_name
    files = get_blob_list(MODULE_SITE_BUCKET_PHOTOS_NAME, species)

    image_urls = {}
    for s in isotype_strains:
      # Get images and thumbs for each strain
      for file in files:
        try:
          start_idx = file.name.index('/')
          end_idx = file.name.index('.')
          file_name = file.name[start_idx+1:end_idx]
        except Exception as ex:
          logger.error(f'Failed to parse image filename "{file.name}" for isotype {isotype_name}: {ex} (file: {file})')
          continue
        if s.strain != file_name:
          continue
        else:
          if '.thumb' in file.name:
            thumb = file.public_url
            image_urls.setdefault(s.strain, {}).update({'thumb': thumb})
          else:
            url = file.public_url
            image_urls.setdefault(s.strain, {}).update({'url': url})

  except Exception as ex:
    logger.error(f'Failed to get images for isotype {isotype_name}: {ex}')

  # Get the single isotype reference strain from the list, returning an error if none is found
  # TODO: Is it possible for there to be more than one? Would this be an error?
  isotype_ref_strain_list = [ x for x in isotype_strains if x.isotype_ref_strain ]
  if len(isotype_ref_strain_list) == 0:
    logger.error(f'Could not find isotype ref strain for isotype "{isotype_name}". List: {isotype_strains}')
    abort(500)

  return render_template('strain/isotype.html', **{
    "title": f"Isotype {isotype_name}",
    "disable_parent_breadcrumb": True,
    "isotype": isotype_strains,
    "isotype_name": isotype_name,
    "isotype_ref_strain": isotype_ref_strain_list[0],
    "strain_json_output": dump_json(isotype_strains),
    "species": species,
    "image_urls": image_urls,
  })
