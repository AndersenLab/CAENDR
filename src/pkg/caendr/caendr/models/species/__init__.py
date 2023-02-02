import json
import os

from logzero import logger

from caendr.models.datastore import WormbaseVersion, WormbaseProjectNumber
from caendr.models.error import BadRequestError, EnvVarError



class Species:


    ## Parameters & Initialization ##

    @classmethod
    def parameters(cls):
        '''
        Parameters that should be provided by keyword when constructing a Species object.
        '''
        return {
            'scientific_name',     # Scientific name of the species (e.g. 'Caenorhabditis elegans')
            'project_num',         # WormBase project number associated with species release (e.g. 'PRJNA13758')
            'wb_ver',              # WormBase version associated with species release (e.g. 'WS276)
            'sva_ver',             # CaeNDR release to use for Strain Variant Annotation
            'latest_release',      # Most recent CaeNDR release that supports the species
            'gene_prefix',         # Species-specific prefix for genes. Will be removed from gene names whenever found.
            'browser_tracks',      # List of browser tracks species supports, by name
        }

    @classmethod
    def properties(cls):
        '''
        All properties of a Species object.  Superset of `Species.parameters()`.
        '''
        return {
            'name',                # Name used to uniquely identify the species
            'short_name',          # Abridged version of scientific name
            *Species.parameters(), # Load the rest of the parameters
        }

    def __init__(self, name, **params):
        '''
        For keyword args, see list of parameters in `Species.parameters()`.

          Args:
            name (str): [Name of the species. Standard format is initial of genus, underscore, species name, e.g. 'c_elegans' for Caenorhabditis elegans.]
        '''

        # Set the species unique name ID
        self.name = name

        # Load parameters from parameter list
        for param in Species.parameters():
            setattr(self, param, params.get(param))

        # Flag any keyword params that aren't in the parameter list, since they will be ignored
        for param in params:
            if param not in Species.parameters():
                logger.warn(f'Unrecognized parameter "{param}" passed to Species constructor. Ignoring value...')



    ## JSON ##

    @classmethod
    def parse_json_file(cls, filename):
        '''
        Read a JSON file, interpreting each top-level element as a new Species object.

          Returns:
            species_list (dict(str, Species)): [A dict mapping species name (ID) to Species objects.]
        '''
        with open(filename) as f:
            species_list = {
                name: Species(name, **params) for name, params in json.load(f).items()
            }
        return species_list


    def __iter__(self):
        yield from { key: getattr(self, key) for key in Species.properties() }.items()



    ## Property: short_name (Short version of scientific name) ##

    @property
    def short_name(self):
        genus, species = self.scientific_name.split()
        return f"{genus[0]}. {species}"



    ## Property: project_num (WormBase Project Number) ##

    @property
    def project_num(self):

        # Throw an error if trying to get the value before it's been set
        if self._project_num is None:
            logger.warning(f"E_NOT_SET: 'project_num' (WormBase project number) for species {self.name}")
            raise BadRequestError()

        # Otherwise, return the value
        return self._project_num

    @project_num.setter
    def project_num(self, new_project_num):
        if new_project_num is None:
            logger.warning(f"Removing WormBase project number for species {self.name}")
            self._project_num = None
        else:
            self._project_num = WormbaseProjectNumber(new_project_num)



    ## Property: wb_ver (WormBase Version) ##

    @property
    def wb_ver(self):

        # Throw an error if trying to get the version before it's been set
        if self._wb_ver is None:
            logger.warning(f"E_NOT_SET: 'wb_ver' (WormBase version) for species {self.name}")
            raise BadRequestError()

        # Otherwise, return the version
        return self._wb_ver

    @wb_ver.setter
    def wb_ver(self, new_wb_ver: str):
        if new_wb_ver is None:
            logger.warning(f"Removing WormBase version for species {self.name}")
            self._wb_ver = None
        else:
            self._wb_ver = WormbaseVersion(new_wb_ver)



    ## Property: sva_ver (CaeNDR Strain Variant Annotation Version) ##

    @property
    def sva_ver(self):
        if not self._sva_ver:
            logger.warning(f"E_NOT_SET: 'sva_ver' (Strain Variant Annotation version) for species {self.name}")
            raise BadRequestError()
        return self._sva_ver

    @sva_ver.setter
    def sva_ver(self, new_sva_ver: str):
        # TODO: validate -- looks like this should be the 8 digit date string
        self._sva_ver = new_sva_ver



# Load species list
SPECIES_LIST_FILE = os.environ['SPECIES_LIST_FILE']
if not SPECIES_LIST_FILE:
    raise EnvVarError()
SPECIES_LIST = Species.parse_json_file(SPECIES_LIST_FILE)
