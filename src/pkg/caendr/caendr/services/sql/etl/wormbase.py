import csv
import gzip
import shutil
import os

from gtfparse import read_gtf_as_dataframe
from logzero import logger

from caendr.models.sql import WormbaseGeneSummary, WormbaseGene, Homolog
from caendr.utils.bio import arm_or_center
from caendr.utils.constants import CHROM_NUMERIC


# https://github.com/phil-bergmann/2016_DLRW_brain/blob/3f69c945a40925101c58a3d77c5621286ad8d787/brain/data.py

def load_genes_summary(self, db):
  '''
    load_genes_summary [extracts gene summary from wormbase db file and loads it into the caendr db]
      Args:
        db (SQLAlchemy): [sqlalchemy db instance to insert into]
  '''  
  logger.info('Loading gene summary table')
  gene_summary = fetch_gene_gff_summary(self.dataset_manager.fetch_gene_gff_db('c_elegans'))
  db.session.bulk_insert_mappings(WormbaseGeneSummary, gene_summary)
  db.session.commit()
  logger.info(f"Inserted {WormbaseGeneSummary.query.count()} Wormbase Gene Summaries")


def load_genes(self, db):
  '''
    load_genes [extracts gene information from wormbase db files and loads it into the caendr db]
      Args:
        db (SQLAlchemy): [sqlalchemy db instance]
  '''  
  logger.info('Extracting gene_gtf file')

  gene_gtf_fname    = 'gene.gtf'
  gene_gtf_gz_fname = self.dataset_manager.fetch_gene_gtf_db('c_elegans')
  gene_ids_fname    = self.dataset_manager.fetch_gene_ids_db('c_elegans')

  with gzip.open(gene_gtf_gz_fname, 'rb') as f_in:
    with open(gene_gtf_fname, 'wb') as f_out:
      shutil.copyfileobj(f_in, f_out)
  logger.info('Done extracting gene_gtf file')

  logger.info('Loading gene table')
  genes = fetch_gene_gtf(gene_gtf_fname, gene_ids_fname)
  db.session.bulk_insert_mappings(WormbaseGene, genes)
  db.session.commit()
  logger.info(f"Inserted {WormbaseGene.query.count()} Wormbase Genes")

  results = db.session.query(WormbaseGene.feature, db.func.count(WormbaseGene.feature)) \
                            .group_by(WormbaseGene.feature) \
                            .all()
  result_summary = '\n'.join([f"{k}: {v}" for k, v in results])
  logger.info(f'Gene Summary: {result_summary}')
  
  
def load_orthologs(self, db):
  logger.info('Loading orthologs from WormBase')
  initial_count = Homolog.query.count()
  orthologs = fetch_orthologs(self.dataset_manager.fetch_ortholog_db('c_elegans'))
  db.session.bulk_insert_mappings(Homolog, orthologs)
  db.session.commit()
  total_records = Homolog.query.count() - initial_count
  logger.info(f'Inserted {total_records} Orthologs')


def get_gene_ids(gene_ids_fname: str):
  """
      Retrieve mapping between wormbase IDs (WB000...) to locus names.
      Uses the latest IDs by default.
      Gene locus names (e.g. pot-2)
  """
  results = [x.split(",")[1:3] for x in gzip.open(gene_ids_fname, 'r').read().decode('utf-8').splitlines()]
  return dict(results)


def fetch_gene_gtf(gtf_fname: str, gene_ids_fname: str):
  """
      LOADS wormbase_gene
      This function fetches and parses the canonical geneset GTF
      and yields a dictionary for each row.
  """
  gene_gtf = read_gtf_as_dataframe(gtf_fname)
  gene_ids = get_gene_ids(gene_ids_fname)

  # Add locus column
  # Rename seqname to chrom
  gene_gtf = gene_gtf.rename({'seqname': 'chrom'}, axis='columns')
  gene_gtf = gene_gtf.assign(locus=[gene_ids.get(x) for x in gene_gtf.gene_id])
  gene_gtf = gene_gtf.assign(chrom_num=[CHROM_NUMERIC[x] for x in gene_gtf.chrom])
  gene_gtf = gene_gtf.assign(pos=(((gene_gtf.end - gene_gtf.start)/2) + gene_gtf.start).map(int))
  gene_gtf.frame = gene_gtf.frame.apply(lambda x: x if x != "." else None)
  gene_gtf.exon_number = gene_gtf.exon_number.apply(lambda x: x if x != "" else None)
  gene_gtf['arm_or_center'] = gene_gtf.apply(lambda row: arm_or_center(row['chrom'], row['pos']), axis=1)
  
  idx = 0
  for row in gene_gtf.to_dict('records'):
    idx += 1
    if os.getenv('USE_MOCK_DATA') and idx > 10:
      logger.warn("USE_MOCK_DATA Early Return!!!")    
      return    
    if idx % 10000 == 0:
      logger.info(f"Processed {idx} lines")
    yield row


def fetch_gene_gff_summary(gff_fname: str):
  """
      LOADS wormbase_gene_summary
      This function fetches data for wormbase_gene_summary;
      It's a condensed version of the wormbase_gene_table
      constructed for convenience.
  """
  WB_GENE_FIELDSET = ['ID', 'biotype', 'sequence_name', 'chrom', 'start', 'end', 'locus']

  with gzip.open(gff_fname) as f:
    idx = 0
    gene_count = 0
    for line in f:
      idx += 1
      if os.getenv("USE_MOCK_DATA") and idx > 100:
        logger.warn("USE_MOCK_DATA Early Exit!!!")    
        return    
      if line.decode('utf-8').startswith("#"):
        continue
      line = line.decode('utf-8').strip().split("\t")
      if idx % 1000000 == 0:
        logger.debug(f"Processed {idx} lines;{gene_count} genes; {line[0]}:{line[4]}")
      if 'WormBase' in line[1] and 'gene' in line[2]:
        gene = dict([x.split("=") for x in line[8].split(";")])
        gene.update(zip(["chrom", "start", "end"],
                        [line[0], line[3], line[4]]))
        gene = {k.lower(): v for k, v in gene.items() if k in WB_GENE_FIELDSET}

        # Change add chrom_num
        gene['chrom_num'] = CHROM_NUMERIC[gene['chrom']]
        gene['start'] = int(gene['start'])
        gene['end'] = int(gene['end'])
        # Annotate gene with arm/center
        gene_pos = int(((gene['end'] - gene['start'])/2) + gene['start'])
        gene['arm_or_center'] = arm_or_center(gene['chrom'], gene_pos)
        if 'id' in gene.keys():
          gene_count += 1
          gene_id_type, gene_id = gene['id'].split(":")
          gene['gene_id_type'], gene['gene_id'] = gene['id'].split(":")

          del gene['id']
          yield gene


def fetch_orthologs(orthologs_fname: str):
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

      # If gene matches, add it to the list
      if ref:
        count += 1
        yield {
          'gene_id': wb_id,
          'gene_name': locus_name,
          'homolog_species': line[0],
          'homolog_taxon_id': None,
          'homolog_gene': line[2],
          'homolog_source': line[3],
          'is_ortholog': line[0] == 'Caenorhabditis elegans',
        }
