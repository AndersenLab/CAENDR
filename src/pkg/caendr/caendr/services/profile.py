import os

from caendr.services.logger import logger

from caendr.services.cloud.datastore import query_ds_entities, get_ds_entity, delete_ds_entity_by_ref
from caendr.services.cloud.storage import upload_blob_from_file_object, generate_blob_url
from caendr.models.datastore.profile import Profile
from caendr.utils.data import unique_id


PROFILE_ROLES = {
  'staff': 'Staff',
  'sac': 'Scientific Advisory Committee',
  'collab': 'Collaborator'
}

def get_profile_role_form_options(): 
  return [(key, val) for key, val in PROFILE_ROLES.items()]
  

def get_all_profiles(keys_only=False):
  ds_entities = query_ds_entities(Profile.kind, keys_only=keys_only)
  return [Profile(e.key.name) for e in ds_entities]


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
  profiles = _get_profiles_with_photos('collab')
  return profiles


def get_committee_profiles():
  logger.debug('Retrieving committee profiles from datastore')
  profiles = _get_profiles_with_photos('sac')
  return profiles



def get_staff_profiles():
  logger.debug('Retrieving staff profiles from datastore')
  profiles = _get_profiles_with_photos('staff')
  return profiles


def _get_profiles_with_photos(prof_role: str):
  # filtering against a list property returns a result if any value in the list matches
  filters = [('prof_roles', '=', prof_role)] 
  ds_entities = query_ds_entities(Profile.kind, filters=filters)
  profiles = []
  bucket = Profile.get_bucket_name()
  for e in ds_entities:
    p = Profile(e)
    if hasattr(p, 'img_blob_path'):
      p.img_url = generate_blob_url(bucket, p.img_blob_path)
    profiles.append(p)
  return profiles
