from .database_operation import DbOp

from .homolog import Homolog
from .strain_annotated_variant import StrainAnnotatedVariant
from .strain import Strain
from .wormbase_gene import WormbaseGene
from .wormbase_gene_summary import WormbaseGeneSummary
from .phenotype import PhenotypeDatabase
from .phenotype_metadata import PhenotypeMetadata

ALL_SQL_TABLES = [
  Strain,
  WormbaseGene,
  WormbaseGeneSummary,
  StrainAnnotatedVariant,
  PhenotypeDatabase,
  PhenotypeMetadata,
]
