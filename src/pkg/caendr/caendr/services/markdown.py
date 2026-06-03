from caendr.services.cloud.datastore import query_ds_entities, get_ds_entity
from caendr.models.datastore import Markdown

CONTENT_TYPES = {
  'help': 'Help'
}


# TODO: Replace with Entity.query_ds call?
def get_all_markdown_content(keys_only=False):
  md_entities = query_ds_entities(Markdown.kind, keys_only=keys_only)
  return [Markdown(e.key.name) for e in md_entities]  


def get_content_type_form_options(): 
  return [(key, val) for key, val in CONTENT_TYPES.items()]
  