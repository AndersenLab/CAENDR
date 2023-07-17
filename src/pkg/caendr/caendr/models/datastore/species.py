from logzero import logger

from caendr.models.datastore import Entity
from caendr.models.datastore import WormbaseVersion, WormbaseProjectNumber
from caendr.models.error import BadRequestError, NotFoundError



class Species(Entity):
    kind = 'species'

    @staticmethod
    def get(species_name):
        return SPECIES_LIST.get(species_name, None)

    @staticmethod
    def from_name(species_name, from_url=False):

        # If allowing URL version, map dashes to underscores
        if from_url:
            species_name = species_name.replace('-', '_')

        # Try to get the species
        species = Species.get(species_name)

        # Raise an error instead of returning None
        if species is not None:
            return species
        raise NotFoundError(Species, {'name': species_name})

    @staticmethod
    def all():
        return SPECIES_LIST


    @classmethod
    def get_props_set(cls):
        return {
            *super().get_props_set(),
            'scientific_name',     # Scientific name of the species (e.g. 'Caenorhabditis elegans')
            'project_num',         # WormBase project number associated with species release (e.g. 'PRJNA13758')
            'wb_ver',              # WormBase version associated with species release (e.g. 'WS276)
            'release_latest',      # Most recent CaeNDR release of this species
            'release_pif',         # CaeNDR release to use for Pairwise Indel Finder
            'release_sva',         # CaeNDR release to use for Strain Variant Annotation
            'gene_prefix',         # Species-specific prefix for genes. Will be removed from gene names whenever found.
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



    ## Property: release_sva (CaeNDR Strain Variant Annotation Version) ##

    @property
    def release_sva(self):
        if not self._release_sva:
            logger.warning(f"E_NOT_SET: 'release_sva' (Strain Variant Annotation version) for species {self.name}")
            raise BadRequestError()
        return self._release_sva

    @release_sva.setter
    def release_sva(self, new_release_sva: str):
        # TODO: validate -- looks like this should be the 8 digit date string
        self._release_sva = new_release_sva



    ## URL variable(s) ##

    def get_url_name(self):
        return self.name.replace('_', '-')



# Load species list
SPECIES_LIST = {
    e.name: e for e in Species.query_ds()
}
SPECIES_LIST = dict(sorted(SPECIES_LIST.items(), key=lambda e: e[1]['order']))
