from caendr.models.datastore import User
from caendr.services.cloud.datastore import delete_ds_entity_by_ref, query_ds_entities


USER_ROLES = {
  'user': 'User',
  'admin': 'Admin'
}

# TODO: Replace with Entity.query_ds call? Should this return as User Entity class?
def get_local_user_by_email(email, user_type='LOCAL'):
    filters = [('email', '=', email), ('user_type', '=', user_type)]
    return query_ds_entities(User.kind, filters=filters)


def get_user_role_form_options(): 
  return [(key, val) for key, val in USER_ROLES.items()]


# TODO: Replace with Entity.query_ds call? Should this return as User Entity class?
def get_all_users(keys_only=False):
  return query_ds_entities(User.kind, keys_only=keys_only)


def delete_user(id):
  delete_ds_entity_by_ref(User.kind, id)


def get_num_registered_users():
  return len(get_all_users(keys_only=True))