import csv
import gzip
import os

from gtfparse import read_gtf_as_dataframe
from caendr.services.logger import logger

from caendr.api.gene import remove_prefix
from caendr.models.sql import WormbaseGeneSummary
from caendr.utils.bio import arm_or_center
from caendr.utils.constants import CHROM_NUMERIC



## Helper Functions ##

def get_gene_ids(species, gene_ids_fname: str):
  """
      Retrieve mapping between wormbase IDs (WB000...) to locus names.
      Uses the latest IDs by default.
      Gene locus names (e.g. pot-2)

      Removes gene prefix from locus names whenever it appears, e.g. 'Cbr-' for C. briggsae.
  """

  # Read in file, and extract the WormBase ID and locus name from each line
  results = [ x.split(",")[1:3] for x in gzip.open(gene_ids_fname, 'r').read().decode('utf-8').splitlines() ]

  # Convert to a dictionary, removing species-specific gene prefix from each value as we do
  return { x[0]: remove_prefix(x[1], species.gene_prefix) for x in results }



## File Parsing Generator Functions ##

def parse_gene_gtf(species, gtf_fname: str, gene_ids_fname: str):
  """
      LOADS wormbase_gene
      This function fetches and parses the canonical geneset GTF
      and yields a dictionary for each row.
  """
  gene_gtf = read_gtf_as_dataframe(gtf_fname)
  gene_ids = get_gene_ids(species, gene_ids_fname)

  # Rename seqname to chrom
  gene_gtf = gene_gtf.rename({'seqname': 'chrom'}, axis='columns')

  # Add locus column
  gene_gtf = gene_gtf.assign(locus=[gene_ids.get(x) for x in gene_gtf.gene_id])

  # Convert chromosomes from roman numerals to integers
  gene_gtf = gene_gtf.assign(chrom_num=[CHROM_NUMERIC[x] for x in gene_gtf.chrom])

  # Compute gene position and add as column
  gene_gtf = gene_gtf.assign(pos=(((gene_gtf.end - gene_gtf.start)/2) + gene_gtf.start).map(int))

  # Remove optional "Gene" prefix from gene IDs to match the wormbase_gene_summary table
  gene_gtf.gene_id = gene_gtf.gene_id.apply(lambda x: remove_prefix(x, 'Gene:'))

  # Convert empty markers to None
  gene_gtf.frame = gene_gtf.frame.apply(lambda x: x if x != "." else None)
  gene_gtf.exon_number = gene_gtf.exon_number.apply(lambda x: x if x != "" else None)

  # Compute whether gene is on arm or center
  gene_gtf['arm_or_center'] = gene_gtf.apply(lambda row: arm_or_center(row['chrom'], row['pos']), axis=1)

  # Add column for species name
  gene_gtf['species_name'] = species.name

  # Loop through and yield all records
  for idx, row in enumerate(gene_gtf.to_dict('records')):

    # If testing, finish early
    if os.getenv('USE_MOCK_DATA') and idx > 10:
      logger.warn("USE_MOCK_DATA Early Return!!!")
      return

    # Progress update
    if idx % 10000 == 0:
      logger.info(f"Processed {idx} lines")

    # Yield the row
    yield row

  logger.debug(f"Processed {idx} lines total for {species.name}")


def parse_gene_gff_summary(species, gff_fname: str):
  """
      LOADS wormbase_gene_summary
      This function fetches data for wormbase_gene_summary;
      It's a condensed version of the wormbase_gene_table
      constructed for convenience.
  """
  WB_GENE_FIELDSET = ['ID', 'biotype', 'sequence_name', 'chrom', 'start', 'end', 'locus', 'species_name']

  with gzip.open(gff_fname) as f:

    # Initialize counter for matching genes
    gene_count = 0

    # Loop through each line in the file (indexed)
    for idx, line in enumerate(f):

      # If testing, finish early
      if os.getenv("USE_MOCK_DATA") and idx > 100:
        logger.warn("USE_MOCK_DATA Early Exit!!!")    
        return

      # Skip comments and pragmas (lines starting with '#' and '##' respectively)
      if line.decode('utf-8').startswith("#"):
        continue

      # Convert the line from a tab-separated string into a list
      line = line.decode('utf-8').strip().split("\t")

      # Progress update
      if idx % 1000000 == 0:
        logger.debug(f"Processed {idx} lines;{gene_count} genes; {line[0]}:{line[4]}")

      # Only parse if line represents a gene from Wormbase
      if ('WormBase' in line[1] or 'AndersenLab' in line[1]) and 'gene' in line[2]:

        # Convert fields column into dict object & include chromosome information
        gene = dict([x.split("=") for x in line[8].split(";")])
        gene.update(zip(["chrom", "start", "end"],
                        [line[0], line[3], line[4]]))
        gene = {k.lower(): v for k, v in gene.items() if k in WB_GENE_FIELDSET}

        # Tag gene with species name
        gene['species_name'] = species.name

        # Change add chrom_num
        gene['chrom_num'] = CHROM_NUMERIC[gene['chrom']]
        gene['start'] = int(gene['start'])
        gene['end'] = int(gene['end'])

        # Annotate gene with arm/center
        gene_pos = int(((gene['end'] - gene['start'])/2) + gene['start'])
        gene['arm_or_center'] = arm_or_center(gene['chrom'], gene_pos)

        # Remove species-specific gene prefix, if locus exists and begins with the prefix
        gene['locus'] = remove_prefix(gene.get('locus'), species.gene_prefix)

        # If gene has an ID, split the ID into two fields and yield the gene
        if 'id' in gene.keys():
          gene_count += 1

          # Split 'id' into 'gene_id_type' and 'gene_id'
          gene['gene_id_type'], gene['gene_id'] = gene['id'].split(":")
          del gene['id']

          # Yield the gene
          yield gene

    logger.debug(f"Processed {idx} lines; {gene_count} genes total for {species.name}")


def parse_orthologs(species, orthologs_fname: str):
  """
      LOADS (part of) homologs
      Fetches orthologs from WormBase, to be stored in the homolog table.
  """
  csv_out = list(csv.reader(open(orthologs_fname, 'r'), delimiter='\t'))

  # Initialize var to track matching ortholog genes
  count = 0

  # Loop through each line in the file
  # TODO: idx is the number of lines processed, which is not the same as the number of records (as claimed in logger statement).
  #       This likely doesn't matter, since it's not used in any actual data, but it's still technically not correct.
  for idx, line in enumerate(csv_out):
    size_of_line = len(line)

    # Skip lines that don't specify an ortholog
    if size_of_line < 2:
      continue

    # Update to next gene
    elif size_of_line == 2:
      wb_id, locus_name = line

    # Parse ortholog
    else:
      ref = WormbaseGeneSummary.query.filter(WormbaseGeneSummary.gene_id == wb_id).first()

      # If testing, finish early
      if os.getenv("USE_MOCK_DATA") and idx > 10:
        logger.warn("USE_MOCK_DATA Early Return!!!")
        return

      # Progress update
      if idx % 10000 == 0:
        logger.info(f'Processed {idx} records yielding {count} inserts')

      # If gene matches, add it to the dataset
      if ref:
        count += 1
        yield {
          'gene_id':          wb_id,
          'gene_name':        locus_name,
          'homolog_species':  line[0],
          'homolog_taxon_id': None,
          'homolog_gene':     line[2],
          'homolog_source':   line[3],
          'is_ortholog':      line[0] == species.scientific_name,
          'species_name':     species.name,
        }
