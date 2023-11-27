from .foreign_resource            import ForeignResource, ForeignResourceTemplate

from caendr.models.datastore      import Species
from caendr.models.error          import ForeignResourceMissingError, ForeignResourceUndefinedError
from caendr.services.cloud.sheets import get_google_sheet



class LocalGoogleSheet(ForeignResource):

  def __init__(self, sheet_id, resource_id = None, species = None):
    self._sheet_id     = sheet_id
    self.__resource_id = resource_id or sheet_id
    self.__species     = species

  def __repr__(self):
    return f'Google Sheet "{self.__resource_id}"' + (f' for {self.__species.name}' if self.__species else '')


  #
  # ForeignResource
  #

  @property
  def metadata(self):
    return {
      'sheet_id': self._sheet_id,
    }

  def fetch_resource(self, use_cache: bool = True):
    try:
      return get_google_sheet( self._sheet_id )
    except Exception as ex:
      raise ForeignResourceMissingError('Google Sheet', self.__resource_id, self.__species) from ex



class LocalGoogleSheetTemplate(ForeignResourceTemplate):
  '''
    Manage a set of Google Sheets, one for each species.

    Implements `SpeciesDict`. Returns Google Sheet object for a given species (see `get_google_sheet`).
  '''

  __sheet_ids = {}

  def __init__(self, resource_id: str, sheet_ids):
    super().__init__(resource_id)
    self.__sheet_ids = sheet_ids

  def __repr__(self):
    return f'Google Sheet Template "{self.resource_id}"'


  #
  # Template Methods
  #

  def get_print_uri(self, species: Species) -> str:
    return f'Google Sheet "{self.resource_id}" for {species.name}'

  def check_exists(self, species: Species) -> bool:
    try:
      get_google_sheet( self.__sheet_ids.get(species.name) )
      return True
    except:
      return False


  def has_for_species(self, species: Species) -> bool:
    return species.name in self.__sheet_ids


  def get_for_species(self, species: Species) -> LocalGoogleSheet:

    # Check that species is valid
    if not self.has_for_species(species):
      raise ForeignResourceUndefinedError('Google Sheet', self.resource_id, species)

    # Create new local sheet object
    return LocalGoogleSheet(self.__sheet_ids[species.name], resource_id=self.resource_id, species=species)
