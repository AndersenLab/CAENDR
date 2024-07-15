from caendr.services.logger import logger

from caendr.utils.constants import CHROM_NUMERIC
from caendr.utils.env import get_env_var

from caendr.services.indel_primer import get_sv_strains



MODULE_SITE_BUCKET_PRIVATE_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')



#
# Query Choices
#


def get_grna_selection_enzymes():
  '''
    Use array as the source of truth so the enzymes can be explicitly ordered.
  '''
  return {
    enzyme_id: enzyme_name for (enzyme_id, enzyme_name) in get_grna_selection_enzyme_choices()
  }

def get_grna_selection_enzyme_choices():
  return [('s_pyogenes_cas9', '*S. pyogenes* Cas9')]


def get_grna_selection_chrom_choices(): 
  return [(x, x) for x in CHROM_NUMERIC.keys()]


def get_grna_selection_strains(species, release = None):
  return get_sv_strains(species, release)



#
# Queries
#

def query_grna_selection(enzyme, species, strain_1, strain_2, chromosome, start, stop):
  return []
