import os
import sys

# Important: We have to load the environment before CaeNDR package imports,
# so global environment variables are available to the CaeNDR package
# TODO: Now that CaeNDR package automatically loads this on initialization,
#       this line isn't necessary - is it better to keep it or remove it?
from caendr.utils.env import load_env
load_env()

from subprocess import Popen, PIPE, STDOUT
from caendr.services.logger import logger

from caendr.utils import monitor
from caendr.models.datastore import IndelPrimerReport
from caendr.services.cloud.storage import download_blob_to_file, upload_blob_from_file, BlobURISchema
from caendr.utils.env import get_env_var, env_log_string

from vcfkit.utils.reference import get_genome_directory



monitor.init_sentry("indel_primer")


#
# Read & Set Environment Variables
#

# Source locations in GCP
MODULE_SITE_BUCKET_PRIVATE_NAME = get_env_var('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_TOOL_PATH                 = get_env_var('INDEL_TOOL_PATH')

# Indel parameters
INDEL_SITE     = get_env_var('INDEL_SITE')
INDEL_STRAIN_1 = get_env_var('INDEL_STRAIN_1')
INDEL_STRAIN_2 = get_env_var('INDEL_STRAIN_2')
SPECIES        = get_env_var('SPECIES')
RELEASE        = get_env_var('RELEASE')

# Result file location
RESULT_BUCKET = get_env_var('RESULT_BUCKET')
RESULT_BLOB   = get_env_var('RESULT_BLOB')

# Name for local cache directory (to download files from GCP)
INDEL_CACHE_DIR = get_env_var('INDEL_CACHE_DIR', '.download')


# Log all environment variables
_env_vars = {
  'INDEL_TOOL_PATH',
  'INDEL_CACHE_DIR',
  'INDEL_SITE',
  'INDEL_STRAIN_1',
  'INDEL_STRAIN_2',
  'SPECIES',
  'RELEASE',
  'RESULT_BUCKET',
  'RESULT_BLOB',
}
logger.info( f'Indel Primer: { env_log_string(vars(), _env_vars) }' )


#
# Download FASTA Reference File(s)
#

# Use VCF-Kit to init / get genome directory
genome_directory = get_genome_directory()

# Construct FASTA file path
fasta_bucket, fasta_path = IndelPrimerReport.get_fasta_filepath(SPECIES, RELEASE, schema=BlobURISchema.PATH)
fasta_file_name = IndelPrimerReport.get_fasta_filename(SPECIES, RELEASE, include_extension=True)

# Define the source and target filenames
# TODO: This adds the .gz extension to the end of the file because it's what VCF-Kit looks for,
#       but this file isn't actually zipped. Does it need to be?
#       (Can accomplish using `bgzip`.)
target_fasta_file_path = os.path.join( genome_directory, fasta_file_name )
target_fasta_file_name = fasta_file_name + '.gz'

# Create a folder at the desired path if one does not yet exist
# NOTE: This will only create one folder down, i.e. genome_directory must already exist and the target path must only be one directory deep.
if not os.path.exists(target_fasta_file_path):
  os.mkdir(target_fasta_file_path)

# Download FASTA file & FASTA index file
if not os.path.exists(os.path.join( target_fasta_file_path, target_fasta_file_name )):
  download_blob_to_file(fasta_bucket, fasta_path,          destination=target_fasta_file_path, filename=target_fasta_file_name)
  download_blob_to_file(fasta_bucket, fasta_path + '.fai', destination=target_fasta_file_path, filename=target_fasta_file_name + '.fai')


#
# Download VCF Files
#

# Generate local name for VCF file
target_vcf_file_path = INDEL_CACHE_DIR
target_vcf_file_name = IndelPrimerReport.get_source_filename(SPECIES, RELEASE) + '.vcf.gz'

# Create a folder at the desired path if one does not yet exist
if not os.path.exists(target_vcf_file_path):
  os.mkdir(target_vcf_file_path)

# Download VCF file & VCF Index file
if not os.path.exists(os.path.join( target_vcf_file_path, target_vcf_file_name )):
  download_blob_to_file(MODULE_SITE_BUCKET_PRIVATE_NAME, INDEL_TOOL_PATH, target_vcf_file_name,          destination=target_vcf_file_path)
  download_blob_to_file(MODULE_SITE_BUCKET_PRIVATE_NAME, INDEL_TOOL_PATH, target_vcf_file_name + '.csi', destination=target_vcf_file_path)


#
# Run VCF-Kit Command
#

# Prepare command for VCF-kit Indel Primer tool
cmd = (
  'conda', 'run', '-n', 'indel-primer',

  # Run VCF-kit indel primer tool
  'vk', 'primer', 'indel',

  # VCF-kit optional parameters
  '--region',      INDEL_SITE,
  '--nprimers',    '10',
  '--polymorphic',
  '--ref',         fasta_path['name'],
  '--samples',     f'{INDEL_STRAIN_1},{INDEL_STRAIN_2}',

  # VCF file to run tool on
  f'{target_vcf_file_path}/{target_vcf_file_name}'
)


# Run VCF-kit command and capture results
with Popen(cmd, stdout=PIPE, stderr=PIPE, bufsize=1) as p, open('results.tsv', 'ab') as file:
  for line in p.stdout: # b'\n'-separated lines
    logger.info(line) # pass bytes as is
    file.write(line)
  for line in p.stderr: # b'\n'-separated lines
    logger.error(sys.stdout.buffer.write(line)) # pass bytes as is


# Upload results to GCP
upload_blob_from_file(RESULT_BUCKET, 'results.tsv', RESULT_BLOB)
