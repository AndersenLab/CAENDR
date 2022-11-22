from .strains import load_strains

from caendr.services.sql.db import DatasetManager

class ETLManager:

    def __init__(self, wb_ver: str = None, sva_ver: str = None):
        self.dataset_manager = DatasetManager(wb_ver=wb_ver, sva_ver=sva_ver)

    def prefetch_all_dbs(self, use_cache: bool = True):
        self.dataset_manager.prefetch_all_external_dbs(use_cache=use_cache)
        self.dataset_manager.prefetch_all_internal_dbs(use_cache=use_cache)


    ## Import functions from this module as class methods ##

    from .wormbase import load_genes_summary, load_genes, load_orthologs
    from .homologs import load_homologs
    from .strain_annotated_variants import load_strain_annotated_variants