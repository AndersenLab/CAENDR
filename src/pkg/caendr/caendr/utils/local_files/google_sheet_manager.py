from caendr.models.datastore   import Species
from caendr.utils.species_dict import SpeciesDict

from caendr.services.cloud.sheets import get_google_sheet



class GoogleSheetManager(SpeciesDict):
  '''
    Manage a set of Google Sheets, one for each species.

    Implements `SpeciesDict`. Returns Google Sheet object for a given species (see `get_google_sheet`).
  '''

  __sheet_ids = {}

  def __init__(self, sheet_ids):
    self.__sheet_ids = sheet_ids

  def get_for_species(self, species: Species):
    return get_google_sheet( self.__sheet_ids.get(species.name) )
