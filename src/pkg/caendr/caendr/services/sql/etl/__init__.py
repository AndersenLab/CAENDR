from .strains import load_strains

from caendr.services.sql.dataset import DatasetManager



class ETLManager:

    def __init__(self, species_list, reload_files: bool = False):
        self.dataset_manager = DatasetManager(species_list=species_list, reload_files=reload_files)

    def prefetch_all_dbs(self, use_cache: bool = True):
        self.dataset_manager.prefetch_all_external_dbs(use_cache=use_cache)
        self.dataset_manager.prefetch_all_internal_dbs(use_cache=use_cache)


    ## Species ##

    @property
    def species_list(self):
        return self.dataset_manager.species_list

    def get_species(self, species_name: str):
        return self.dataset_manager.get_species(species_name)


    ## Download Path ##

    @property
    def local_download_path(self):
        return self.dataset_manager.local_download_path

    def get_download_path(self, species_name):
        return f"{self.local_download_path}/{species_name}"

    def unzip_gz(self, *args):
        '''
            Directly calls the unzip_gz method this object's DatasetManager for the given arguments.
        '''
        return self.dataset_manager.unzip_gz(*args)


    ## Import functions from this module as class methods ##

    from ._load_table import (
        load_table,
        load_genes_summary,
        load_genes,
        load_strain_annotated_variants,
    )
