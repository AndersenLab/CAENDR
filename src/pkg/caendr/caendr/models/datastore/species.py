from logzero import logger

from caendr.models.datastore import Entity
from caendr.models.datastore import WormbaseVersion, WormbaseProjectNumber
from caendr.models.error import BadRequestError, NotFoundError



class Species(Entity):
    kind = 'species'

    @staticmethod
    def get(species_name):
        if species_name in SPECIES_LIST:
            return SPECIES_LIST[species_name]
        raise NotFoundError(Species, {'name': species_name})


    @classmethod
    def get_props_set(cls):
        return {
            *super().get_props_set(),
            'scientific_name',     # Scientific name of the species (e.g. 'Caenorhabditis elegans')
            'project_num',         # WormBase project number associated with species release (e.g. 'PRJNA13758')
            'wb_ver',              # WormBase version associated with species release (e.g. 'WS276)
            'sva_ver',             # CaeNDR release to use for Strain Variant Annotation
            'latest_release',      # Most recent CaeNDR release that supports the species
            'indel_primer_ver',
            'gene_prefix',         # Species-specific prefix for genes. Will be removed from gene names whenever found.
            'browser_tracks',      # List of browser tracks species supports, by name
            'order',
        }



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


    def get_url_name(self):
        return self.name.replace('_', '-')



# Load species list
SPECIES_LIST = {
    e.name: e for e in Species.query_ds()
}
SPECIES_LIST = dict(sorted(SPECIES_LIST.items(), key=lambda e: e[1]['order']))