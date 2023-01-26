import os

from caendr.services.logger import logger

from caendr.services.cloud.datastore import query_ds_entities, get_ds_entity, delete_ds_entity_by_ref
from caendr.services.cloud.storage import upload_blob_from_file_object, generate_blob_url
from caendr.models.datastore.profile import Profile
from caendr.utils.data import unique_id


# TODO: Move to Profile class
PROFILE_ROLES = {
  'staff': 'Staff',
  'sac': 'Scientific Advisory Committee',
  'collab': 'Collaborator'
}

def get_profile_role_form_options(): 
  return [(key, val) for key, val in PROFILE_ROLES.items()]
  

def get_all_profiles():
  return Profile.query_ds()


def get_profile(id: str):
  p = Profile(id)
  if not p:
    raise UnprocessableEntity('Profile - {id} does not exist.')
  return p


def delete_profile(id):
  delete_ds_entity_by_ref(Profile.kind, id)
  

def create_new_profile(**kwargs):
  logger.debug(f'Creating new Profile: **kwargs:{kwargs}')
  id = unique_id()
  p = Profile(id)
  p.set_properties(id=id)
  p.set_properties(**kwargs)
  p.save()
  return p


def upload_profile_photo(p, file):
  logger.debug(f'Uploading Profile photo: p:{p} file:{file}')
  bucket = p.get_bucket_name()
  prefix = p.get_blob_prefix()
  blob_name = f'{prefix}/{p.id}.jpg'
  upload_blob_from_file_object(bucket, file, blob_name)
  p.set_properties(img_blob_path=blob_name)
  p.save()


def get_profile_photo_url(p):
  bucket = p.get_bucket_name()
  if hasattr(p, img_blob_path):
    return generate_blob_url(bucket, p.img_blob_path)
  return None


def update_profile(p, **kwargs):
  logger.debug(f'Updating existing profile: **kwargs:{kwargs}')
  p.set_properties(**kwargs)
  p.save()
  return p



def get_collaborator_profiles():
  logger.debug('Retrieving collaborator profiles from datastore')

  # Filtering against a list property returns a result if any value in the list matches
  return Profile.query_ds( filters = [('prof_roles', '=', 'collab')] )


def get_committee_profiles():
  logger.debug('Retrieving committee profiles from datastore')

  # Filtering against a list property returns a result if any value in the list matches
  return Profile.query_ds( filters = [('prof_roles', '=', 'sac')] )


def get_staff_profiles():
  logger.debug('Retrieving staff profiles from datastore')

  # Filtering against a list property returns a result if any value in the list matches
  return Profile.query_ds( filters = [('prof_roles', '=', 'staff')] )
