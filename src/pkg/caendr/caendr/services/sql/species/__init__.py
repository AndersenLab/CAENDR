import json
import re

from logzero import logger

from caendr.models.error import BadRequestError, InternalError



class Species:
    def __init__(self, name, proj_num, wb_ver, sva_ver):
        '''
          Args:
            name (str): [Name of the species. Standard format is initial of genus, underscore, species name, e.g. 'c_elegans' for Caenorhabditis elegans.]
            proj_num (str): [WormBase project number to use (e.g. 'PRJNA13758').]
            wb_ver (str): [Version of WormBase data to use (e.g. 'WS276').]
            sva_ver (str): [Strain Variant Annotation version to use.]
        '''
        self.name     = name
        self.proj_num = proj_num
        self.wb_ver   = wb_ver
        self.sva_ver  = sva_ver


    @classmethod
    def from_json(cls, key, value):
        return Species(
            key,
            value['project_number'],
            value['wormbase_version'],
            value['sva_version']
        )


    @classmethod
    def parse_json_file(cls, filename):
        with open(filename) as f:
            species_list = {
                key: Species.from_json(key, val) for key, val in json.load(f).items()
            }
        return species_list


    ## Property: name (Species Name) ##

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name: str):
        self._name = new_name


    ## Property: proj_num (Project Number) ##

    @property
    def proj_num(self):
        return self._proj_num

    @proj_num.setter
    def proj_num(self, new_proj_num):
        # TODO: Validate?
        self._proj_num = new_proj_num


    ## Property: wb_ver (WormBase Version) ##

    @property
    def wb_ver(self):

        # Throw an error if trying to get the version before it's been set
        if not self._wb_ver:
            logger.warning(f"E_NOT_SET: 'wb_ver' (WormBase version) for species {self.name}")
            raise BadRequestError()

        # Otherwise, return the version
        return self._wb_ver

    @wb_ver.setter
    def wb_ver(self, new_wb_ver: str):

        # Validate desired new value mtches expected format 'WS###', e.g. 'WS276'
        # TODO: Confirm this is the correct format
        # TODO: What about WormBase ParaSite?
        if not re.match(r'^WS[0-9]+$', new_wb_ver):
            logger.warning(f'Invalid WormBase Version String: "{new_wb_ver}"')
            raise InternalError()

        # If valid, set the new value
        self._wb_ver = new_wb_ver


    ## Property: sva_ver (Strain Variant Annotation Version) ##

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
