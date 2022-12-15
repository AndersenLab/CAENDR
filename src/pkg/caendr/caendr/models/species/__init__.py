import json
import re

from logzero import logger

from caendr.models.datastore import WormbaseVersion, WormbaseProjectNumber
from caendr.models.error import BadRequestError, InternalError



class Species:
    def __init__(self, name, **params):
        '''
          Args:
            name (str): [Name of the species. Standard format is initial of genus, underscore, species name, e.g. 'c_elegans' for Caenorhabditis elegans.]

          Keyword Args:
            project_number (str): [WormBase project number to use (e.g. 'PRJNA13758').]
            wormbase_version (str): [Version of WormBase data to use (e.g. 'WS276').]
            sva_version (str): [Strain Variant Annotation version to use.]
            scientific_name (str): [Scientific name of the species.]
            homolog_prefix (str): [Species-specific prefix for some genes. Will be removed from gene names.]
            homolog_id (int): [.]
        '''
        self.name = name

        # Set scientific name
        self.scientific_name = params["scientific_name"]

        # Set versioning information
        self.proj_num = params["project_number"]
        self.wb_ver   = params["wormbase_version"]
        self.sva_ver  = params["sva_version"]
        self.latest   = params["latest_release"]

        # Set params for homologs
        self.homolog_prefix = params.get('homolog_prefix', '')
        self.homolog_id     = params.get('homolog_id',     None)



    ## JSON ##

    @classmethod
    def parse_json_file(cls, filename):
        with open(filename) as f:
            species_list = {
                name: Species(name, **params) for name, params in json.load(f).items()
            }
        return species_list


    def __iter__(self):
        yield from {
            'name':             self.name,
            'scientific_name':  self.scientific_name,
            'short_name':       self.short_name,
            'project_number':   self.proj_num,
            'wormbase_version': self.wb_ver,
            'sva_version':      self.sva_ver,
            'latest_release':   self.latest,
        }.items()



    ## Property: name (Species Name) ##

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name: str):
        self._name = new_name


    @property
    def short_name(self):
        genus, species = self.scientific_name.split()
        return f"{genus[0]}. {species}"



    ## Property: proj_num (Project Number) ##

    @property
    def proj_num(self):

        # Throw an error if trying to get the value before it's been set
        if self._proj_num is None:
            logger.warning(f"E_NOT_SET: 'proj_num' (WormBase project number) for species {self.name}")
            raise BadRequestError()

        # Otherwise, return the value
        return self._proj_num

    @proj_num.setter
    def proj_num(self, new_proj_num):
        if new_proj_num is None:
            logger.warning(f"Removing WormBase project number for species {self.name}")
            self._proj_num = None
        else:
            self._proj_num = WormbaseProjectNumber(new_proj_num)



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
