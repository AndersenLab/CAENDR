from abc import ABC, abstractmethod

from caendr.models.datastore import Species



class ForeignResource(ABC):
  '''
    Generic interface for accessing a foreign resource and making it available locally.
    This may be a datastore file, a sheet, etc.
  '''

  @property
  @abstractmethod
  def metadata(self):
    '''
      Any metadata associated with the resource.
    '''
    return {}

  def fetch(self, use_cache: bool = True):
    '''
      Fetch the desired resource, making it available locally.  Returns this object itself.

      Raises:
        - `ForeignResourceMissingError`: The desired resource could not be found.
    '''
    self.fetch_resource(use_cache=use_cache)
    return self

  @abstractmethod
  def fetch_resource(self, use_cache: bool = True):
    '''
      Fetch the desired resource, making it available locally, then return the local resource directly.

      Raises:
        - `ForeignResourceMissingError`: The desired resource could not be found.
    '''
    pass



class ForeignResourceTemplate(ABC):
  '''
    Generic interface for managing a set of foreign resources
    which follow the same template and are each specific to one species.
  '''

  @abstractmethod
  def get_print_uri(self, species: Species) -> str:
    '''
      Get a string representing the foreign resource, for printing.
    '''
    pass

  @abstractmethod
  def check_exists(self, species: Species) -> bool:
    '''
      Check whether the foreign resource exists for the given species.
    '''
    pass

  @abstractmethod
  def has_for_species(self, species: Species) -> bool:
    '''
      Check whether this object is tracking a resource for the given species.
    '''
    pass

  @abstractmethod
  def get_for_species(self, species: Species) -> ForeignResource:
    '''
      Fetch the tracked resource for the given species and return it
      as a `ForeignResource` object.

      Raises:
        - `ForeignResourceUndefinedError`: The template cannot be instantiated for the given species.
    '''
    pass
