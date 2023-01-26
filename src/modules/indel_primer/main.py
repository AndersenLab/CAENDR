import os
import sys

from subprocess import Popen, PIPE, STDOUT
from caendr.services.logger import logger
from dotenv import load_dotenv

from caendr.utils import monitor
from caendr.models.error import EnvVarError
from caendr.services.cloud.storage import download_blob_to_file, upload_blob_from_file



dotenv_file = '.env'
load_dotenv(dotenv_file)

monitor.init_sentry("indel_primer")


# Source locations in GCP
MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')
INDEL_TOOL_PATH                 = os.environ.get('INDEL_TOOL_PATH')

# Indel parameters
INDEL_SITE     = os.environ.get('INDEL_SITE')
INDEL_STRAIN_1 = os.environ.get('INDEL_STRAIN_1')
INDEL_STRAIN_2 = os.environ.get('INDEL_STRAIN_2')

# Result file location
RESULT_BUCKET = os.environ.get('RESULT_BUCKET')
RESULT_BLOB   = os.environ.get('RESULT_BLOB')

# Names of source files
SV_BED_FILENAME = os.environ.get('INDEL_PRIMER_SV_BED_FILENAME')
SV_VCF_FILENAME = os.environ.get('INDEL_PRIMER_SV_VCF_FILENAME')

# WormBase Version
WORMBASE_VERSION  = os.environ.get('WORMBASE_VERSION')

# Name for local cache directory (to download files from GCP)
INDEL_CACHE_DIR = os.environ.get('INDEL_CACHE_DIR')


# Log all env vars
logger.info(f'Indel Primer: INDEL_SITE:{INDEL_SITE} INDEL_STRAIN_1:{INDEL_STRAIN_1} INDEL_STRAIN_2:{INDEL_STRAIN_2} WORMBASE_VERSION:{WORMBASE_VERSION} RESULT_BUCKET:{RESULT_BUCKET} RESULT_BLOB:{RESULT_BLOB} SV_BED_FILENAME:{SV_BED_FILENAME} SV_VCF_FILENAME:{SV_VCF_FILENAME}')

# Ensure all env vars exist
if not INDEL_SITE or not INDEL_STRAIN_1 or not INDEL_STRAIN_2 or not RESULT_BLOB or not RESULT_BUCKET or not WORMBASE_VERSION or not SV_BED_FILENAME or not SV_VCF_FILENAME or not INDEL_TOOL_PATH or not INDEL_CACHE_DIR:
  raise EnvVarError()



# Generate local name for VCF file
target_vcf_file_name = f'{INDEL_CACHE_DIR}/{SV_VCF_FILENAME}'

# Create a folder at the desired path if one does not yet exist
if not os.path.exists(INDEL_CACHE_DIR):
  os.mkdir(INDEL_CACHE_DIR)

# Download VCF file
# Index too?
if not os.path.exists(target_vcf_file_name):
  download_blob_to_file(MODULE_SITE_BUCKET_PRIVATE_NAME, f'{INDEL_TOOL_PATH}/{SV_VCF_FILENAME}', target_vcf_file_name)


# Prepare command for VCF-kit Indel Primer tool
cmd = (
  'conda', 'run', '-n', 'indel-primer',

  # Run VCF-kit indel primer tool
  'vk', 'primer', 'indel',

  # VCF-kit optional parameters
  '--region',      INDEL_SITE,
  '--nprimers',    '10',
  '--polymorphic',
  '--ref',         WORMBASE_VERSION,
  '--samples',     f'{INDEL_STRAIN_1},{INDEL_STRAIN_2}',

  # VCF file to run tool on
  target_vcf_file_name
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
