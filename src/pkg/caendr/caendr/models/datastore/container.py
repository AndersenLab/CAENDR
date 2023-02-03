from caendr.services.logger import logger

from caendr.models.datastore import Entity
from caendr.models.error import NotFoundError

class Container(Entity):
  kind = 'container'

  def __repr__(self):
    name = getattr(self, 'name', 'no-name')
    if hasattr(self, 'container_tag'):
      name += ':' + self['container_tag']
    return f"<{self.kind}:{name}>"

  @classmethod
  def get_props_set(cls):
    return {
      *super(Container, cls).get_props_set(),
      'repo',
      'container_name',
      'container_registry',
      'container_tag',
    }

  def uri(self):
    s = f"{self['repo']}/{self['container_name']}"
    if self['container_tag']:
      s += ':' + self['container_tag']
    return s


  @classmethod
  def get_current_version(cls, container_name: str):
    '''
      Gets the most recent version of the container with the given name.
      Raises a NotFoundError if no matching containers could be found.
    '''

    # Query for all containers matching the given name
    all_versions = cls.query_ds( filters = [('container_name', '=', container_name)] )

    # If matching version(s) found, return the most recent
    if len(all_versions):
      logger.debug(all_versions)
      return all_versions[0]

    # Otherwise, raise an error
    else:
      logger.error(f'Unable to find container named "{container_name}".')
      raise NotFoundError(f'Unable to find container named "{container_name}".')
