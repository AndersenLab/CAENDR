from caendr.services.logger import logger

from caendr.utils.constants import CHROM_NUMERIC
from caendr.utils.env import get_env_var

from caendr.services.indel_primer import get_sv_strains



MODULE_SITE_BUCKET_PRIVATE_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')



#
# Query Choices
#


def get_crispr_method_choices():
  return [('cas9', 'cas9')]


def get_crispr_chrom_choices(): 
  return [(x, x) for x in CHROM_NUMERIC.keys()]


def get_crispr_strains(species, release = None):
  return get_sv_strains(species, release)



#
# Queries
#

def query_crispr(method, species, strain_1, strain_2, chromosome, start, stop):
  return []
