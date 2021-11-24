from caendr.models.datastore import User
from caendr.services.cloud.datastore import delete_ds_entity_by_ref, query_ds_entities


def get_all_users(keys_only=False):
  return query_ds_entities(User.kind, keys_only=keys_only)

def delete_user(id):
  delete_ds_entity_by_ref(User.kind, id)

def get_num_registered_users():
  return len(get_all_users(keys_only=True))