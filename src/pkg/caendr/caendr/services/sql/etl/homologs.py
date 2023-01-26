import re
import tarfile
import csv
import os

from caendr.services.logger import logger
from urllib.request import urlretrieve
from tempfile import NamedTemporaryFile

from caendr.models.sql import WormbaseGeneSummary
from caendr.services.sql.dataset import TAXON_ID_URL



def fetch_taxon_ids():
  """
      Downloads mapping of taxonomic IDs to species names.
  """
  # TODO: combine fetching taxonomic ids with the rest of the external DBs
  taxon_file = NamedTemporaryFile(suffix='tar')
  out, err = urlretrieve(TAXON_ID_URL, taxon_file.name)
  tar = tarfile.open(out)
  # Read names file
  names_dmp = tar.extractfile('names.dmp')
  names_dmp = names_dmp.read().decode('utf-8').splitlines()
  lines = [re.split(r"\t\|[\t]?", x) for x in names_dmp]
  taxon_ids = {int(l[0]): l[1] for l in lines if l[3] == 'scientific name'}
  return taxon_ids


def parse_homologene(species, homologene_fname: str):
  """
    Download the homologene database and load

    Output dictionary has the following structure:

      {
        'hid': '2188',
        'taxon_id': '7165'
        'gene_id': '1280005',
        'ce_gene_name': 'Y97E10AL.3',
        'gene_symbol': 'AgaP_AGAP009047',
        'protein_accession': 'XP_319799.4',
        'protein_gi': '158299762',
        'species': 'Anopheles gambiae',
      }

      * hid = Homolog ID: Assigned to multiple lines; a group genes that are homologous
      * taxon_id = NCBI taxonomic ID
      * gene_id = NCBI Entrez ID
      * gene_symbol = Gene Symbol
      * species = species name
  """
  response_csv = list(csv.reader(open(homologene_fname, 'r'), delimiter='\t'))

  taxon_ids = fetch_taxon_ids()

  # First, fetch records with a homolog ID that possesses a gene for the current species
  species_set = dict([[int(x[0]), x[3]] for x in response_csv if x[1] == str(species.homolog_id)])

  # Remove species-specific prefix from some gene names
  for k, v in species_set.items():
    species_set[k] = v.replace(species.homolog_prefix, '')

  # Initialize counter for matching homologs
  count = 0

  # Loop through each line in the file (indexed)
  for idx, line in enumerate(response_csv):

    # If testing, finish early
    if os.getenv('USE_MOCK_DATA') and idx > 10:
      logger.warn("USE_MOCK_DATA Early Return!!!")
      return

    # Read IDs
    tax_id = int(line[1])
    homolog_id = int(line[0])

    if homolog_id in species_set.keys() and tax_id != int(species.homolog_id):

      # Try to resolve the wormbase WB ID if possible.
      gene_name = species_set[homolog_id]
      gene_id = WormbaseGeneSummary.resolve_gene_id(gene_name)
      ref = WormbaseGeneSummary.query.filter(WormbaseGeneSummary.gene_id == gene_id).first()

      # Progress update
      if idx % 10000 == 0:
        logger.info(f'Processed {idx} records yielding {count} inserts')

      # If gene matches, add it to the dataset
      if ref:
        count += 1
        yield {
          'gene_id':          gene_id,
          'gene_name':        gene_name,
          'homolog_species':  taxon_ids[tax_id],
          'homolog_taxon_id': tax_id,
          'homolog_gene':     line[3],
          'homolog_source':   "Homologene",
          'is_ortholog':      False,
          'species_name':     species.name,
        }
