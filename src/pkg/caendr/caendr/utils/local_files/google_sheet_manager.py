from .foreign_resource_watcher    import ForeignResourceWatcher

from caendr.models.datastore      import Species
from caendr.models.error          import ForeignResourceMissingError
from caendr.services.cloud.sheets import get_google_sheet



class GoogleSheetManager(ForeignResourceWatcher):
  '''
    Manage a set of Google Sheets, one for each species.

    Implements `SpeciesDict`. Returns Google Sheet object for a given species (see `get_google_sheet`).
  '''

  __sheet_ids = {}

  def __init__(self, resource_id, sheet_ids):
    self.__resource_id = resource_id
    self.__sheet_ids = sheet_ids


  #
  # Template Methods
  #

  def get_print_uri(self, species: Species) -> str:
    return f'Google Sheet "{self.__resource_id}" for {species.name}'

  def check_exists(self, species: Species) -> bool:
    try:
      get_google_sheet( self.__sheet_ids.get(species.name) )
      return True
    except:
      return False

  def has_for_species(self, species: Species) -> bool:
    return species.name in self.__sheet_ids

  def get_for_species(self, species: Species):
    try:
      return get_google_sheet( self.__sheet_ids.get(species.name) )
    except Exception as ex:
      raise ForeignResourceMissingError('Google Sheet', self.__resource_id, species) from ex
