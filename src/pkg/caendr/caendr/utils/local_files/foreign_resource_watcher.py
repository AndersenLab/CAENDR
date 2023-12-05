from abc    import ABC, abstractmethod
from typing import Any

from caendr.models.datastore import Species



class ForeignResourceWatcher(ABC):
  '''
    Generic interface for classes that manage foreign (non-local) resources (datastore files, sheets, etc)
    which are specific to one or more species.
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
      Check whether the foreign resource exists.
    '''
    pass

  @abstractmethod
  def has_for_species(self, species: Species) -> bool:
    '''
      Check whether this object is tracking a resource for the given species.
    '''
    pass

  @abstractmethod
  def get_for_species(self, species: Species) -> Any:
    '''
      Fetch the tracked resource for the given species and return it.
      Format of the returned object depends on subclass.
    '''
    pass
