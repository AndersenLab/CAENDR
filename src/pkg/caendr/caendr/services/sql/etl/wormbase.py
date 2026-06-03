import csv
import gzip
import shutil
import os

from gtfparse import read_gtf_as_dataframe
from caendr.services.logger import logger

from caendr.models.sql import WormbaseGeneSummary, WormbaseGene, Homolog
from caendr.utils.bio import arm_or_center
from caendr.utils.constants import CHROM_NUMERIC
from caendr.services.sql.db import bulk_insert_with_batching, load_with_copy_from_generator, rebuild_indexes


# https://github.com/phil-bergmann/2016_DLRW_brain/blob/3f69c945a40925101c58a3d77c5621286ad8d787/brain/data.py

def load_genes_summary(db, gene_gff_fname: str, use_copy: bool = True):
  '''
    load_genes_summary [extracts gene summary from wormbase db file and loads it into the caendr db]
      Args:
        db (SQLAlchemy): [sqlalchemy db instance to insert into]
        gene_gff_fname (str): [path of downloaded wormbase gene gff file]
        use_copy (bool): [whether to use COPY command for faster loading (default True)]
  '''  
  logger.info('Loading gene summary table')
  gene_summary = fetch_gene_gff_summary(gene_gff_fname)
  
  if use_copy:
    try:
      total_inserted = load_with_copy_from_generator(
        db,
        'wormbase_gene_summary',
        gene_summary,
        fieldnames=['ID', 'biotype', 'sequence_name', 'chrom', 'start', 'end', 'locus', 'chrom_num', 'arm_or_center', 'gene_id_type', 'gene_id'],
        disable_indexes_flag=True
      )
      rebuild_indexes(db, 'wormbase_gene_summary')
      logger.info(f"Inserted {total_inserted} Wormbase Gene Summaries (using COPY command)")
      return total_inserted
    except Exception as e:
      logger.warning(f'COPY command failed, falling back to batched inserts: {e}')
      gene_summary = fetch_gene_gff_summary(gene_gff_fname)
  
  total_inserted = bulk_insert_with_batching(
    db, 
    WormbaseGeneSummary, 
    gene_summary, 
    batch_size=10000,
    defer_fks=True
  )
  logger.info(f"Inserted {total_inserted} Wormbase Gene Summaries")
  return total_inserted
  
  
def load_genes(db, gene_gtf_gz_fname: str, gene_ids_fname: str, use_copy: bool = True):
  '''
    load_genes [extracts gene information from wormbase db files and loads it into the caendr db]
      Args:
        db (SQLAlchemy): [sqlalchemy db instance]
        gene_gtf_gz_fname (str): [path of downloaded wormbase gene gtf.gz file]
        gene_ids_fname (str): [path of downloaded wormbase gene IDs file]
        use_copy (bool): [whether to use COPY command for faster loading (default True)]
  '''  
  logger.info('Extracting gene_gtf file')
  gene_gtf_fname = 'gene.gtf'
  with gzip.open(gene_gtf_gz_fname, 'rb') as f_in:
    with open(gene_gtf_fname, 'wb') as f_out:
      shutil.copyfileobj(f_in, f_out)
  logger.info('Done extracting gene_gtf file')


  logger.info('Loading gene table')
  genes = fetch_gene_gtf(gene_gtf_fname, gene_ids_fname)
  
  if use_copy:
    try:
      # Get fieldnames from first row
      genes_list = list(genes)
      if genes_list:
        fieldnames = list(genes_list[0].keys())
        # Create new generator from list
        genes_gen = (row for row in genes_list)
        
        total_inserted = load_with_copy_from_generator(
          db,
          'wormbase_gene',
          genes_gen,
          fieldnames=fieldnames,
          disable_indexes_flag=True
        )
        rebuild_indexes(db, 'wormbase_gene')
        logger.info(f"Inserted {total_inserted} Wormbase Genes (using COPY command)")
      else:
        total_inserted = 0
        logger.warning("No genes to load")
    except Exception as e:
      logger.warning(f'COPY command failed, falling back to batched inserts: {e}')
      genes = fetch_gene_gtf(gene_gtf_fname, gene_ids_fname)
      total_inserted = bulk_insert_with_batching(
        db, 
        WormbaseGene, 
        genes, 
        batch_size=10000,
        defer_fks=True
      )
  else:
    total_inserted = bulk_insert_with_batching(
      db, 
      WormbaseGene, 
      genes, 
      batch_size=10000,
      defer_fks=True
    )
  
  logger.info(f"Inserted {total_inserted} Wormbase Genes")

  results = db.session.query(WormbaseGene.feature, db.func.count(WormbaseGene.feature)) \
                            .group_by(WormbaseGene.feature) \
                            .all()
  result_summary = '\n'.join([f"{k}: {v}" for k, v in results])
  logger.info(f'Gene Summary: {result_summary}')
  
  
def load_orthologs(db, ortholog_fname: str, use_copy: bool = True):
  logger.info('Loading orthologs from WormBase')
  orthologs = fetch_orthologs(ortholog_fname)
  
  if use_copy:
    try:
      orthologs_list = list(orthologs)
      if orthologs_list:
        fieldnames = list(orthologs_list[0].keys())
        orthologs_gen = (row for row in orthologs_list)
        
        total_inserted = load_with_copy_from_generator(
          db,
          'homolog',
          orthologs_gen,
          fieldnames=fieldnames,
          disable_indexes_flag=True
        )
        rebuild_indexes(db, 'homolog')
        logger.info(f'Inserted {total_inserted} Orthologs (using COPY command)')
        return total_inserted
      else:
        total_inserted = 0
        logger.warning("No orthologs to load")
    except Exception as e:
      logger.warning(f'COPY command failed, falling back to batched inserts: {e}')
      orthologs = fetch_orthologs(ortholog_fname)
  
  total_inserted = bulk_insert_with_batching(
    db, 
    Homolog, 
    orthologs, 
    batch_size=10000,
    defer_fks=True
  )
  logger.info(f'Inserted {total_inserted} Orthologs')
  return total_inserted


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
      Fetches orthologs from wormbase; Stored in the homolog table.
  """
  csv_out = list(csv.reader(open(orthologs_fname, 'r'), delimiter='\t'))

  idx = 0
  count = 0
  for line in csv_out:
    idx += 1
    size_of_line = len(line)
    if size_of_line < 2:
      continue
    elif size_of_line == 2:
      wb_id, locus_name = line
    else:
      ref = WormbaseGeneSummary.query.filter(WormbaseGeneSummary.gene_id == wb_id).first()
      if os.getenv("USE_MOCK_DATA") and idx > 10:
        logger.warn("USE_MOCK_DATA Early Return!!!")    
        return    
      if idx % 10000 == 0:
        logger.info(f'Processed {idx} records yielding {count} inserts')
      if ref:
        count += 1
        yield {'gene_id': wb_id,
                'gene_name': locus_name,
                'homolog_species': line[0],
                'homolog_taxon_id': None,
                'homolog_gene': line[2],
                'homolog_source': line[3],
                'is_ortholog': line[0] == 'Caenorhabditis elegans'}
