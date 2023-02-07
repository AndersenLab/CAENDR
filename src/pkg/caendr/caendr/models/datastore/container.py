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
  def get(cls, name: str, version: str = None):
    '''
      Gets the container matching the given name and version tag.
      If version is not provided, returns the current version.

      Raises:
        NotFoundError: No matching container could be found.
    '''

    # Create list of filters
    filters = [('container_name', '=', name)]
    if version is not None:
      filters += [('container_version', '=', version)]

    # Query for all matching containers
    matches = cls.query_ds( filters = filters )

    # If matching version(s) found, return the most recent
    if len(matches):
      logger.debug(matches)
      return matches[0]

    # Otherwise, raise an error
    else:
      if version is None:
        logger.error(f'Unable to find container "{name}".')
        raise NotFoundError(f'Unable to find container "{name}".')
      else:
        logger.error(f'Unable to find container "{name}" with version "{version}".')
        raise NotFoundError(f'Unable to find container "{name}" with version "{version}".')


  @classmethod
  def get_current_version(cls, container_name: str):
    '''
      Gets the most recent version of the container with the given name.
      Equivalent to Container.get() with no version argument provided.

      Raises:
        NotFoundError: No matching container could be found.
    '''
    return Container.get(container_name)
