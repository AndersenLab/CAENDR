from abc import ABC, abstractmethod

from caendr.models.datastore import Species



class SpeciesDict(ABC):
  '''
    Generic interface for classes that store data specific to one or more species.
  '''

  @abstractmethod
  def get_for_species(self, species: Species):
    '''
      Return fetched data for the given species. Format depends on subclass.
    '''
    pass
