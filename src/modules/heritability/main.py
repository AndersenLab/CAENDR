import os
import sys

from subprocess import Popen, PIPE, STDOUT
from logzero import logger
from dotenv import load_dotenv

from caendr.utils import monitor
from caendr.models.error import EnvVarError
from caendr.services.cloud.storage import download_blob_to_file, upload_blob_from_file
from caendr.utils.file import write_string_to_file

dotenv_file = '.env'
load_dotenv(dotenv_file)

monitor.init_sentry("heritability")

DATA_HASH = os.environ.get('DATA_HASH')
DATA_BUCKET = os.environ.get('DATA_BUCKET')
DATA_BLOB_PATH = os.environ.get('DATA_BLOB_PATH')
DATA_BLOB_NAME = os.environ.get('DATA_BLOB_NAME', 'data.tsv')
RESULT_BLOB_NAME = os.environ.get('RESULT_BLOB_NAME', 'result.tsv')

logger.info(f'Heritability: DATA_BUCKET:{DATA_BUCKET} DATA_BLOB_PATH:{DATA_BLOB_PATH} DATA_BLOB_NAME:{DATA_BLOB_NAME} RESULT_BLOB_NAME:{RESULT_BLOB_NAME} DATA_HASH:{DATA_HASH}')

if not DATA_BUCKET or not DATA_BLOB_PATH or not DATA_BLOB_NAME or not RESULT_BLOB_NAME or not DATA_HASH:
  raise EnvVarError()


data_blob = f'{DATA_BLOB_PATH}/{DATA_BLOB_NAME}'
result_blob = f'{DATA_BLOB_PATH}/{RESULT_BLOB_NAME}'
log_fname = 'output.log'
data_fname = 'data.tsv'
result_fname = 'result.tsv'
hash_fname = 'hash.txt'
strain_data_fname = 'strain_data.tsv'
script_fname = 'H2_script.R'
heritability_version = "v2"

download_blob_to_file(DATA_BUCKET, data_blob, data_fname)

# Write hash to file- not sure why this is needed by the RScript call though?
write_string_to_file(f'{DATA_HASH}/n', hash_fname)

cmd = ('conda', 
        'run',
        '-n',
        'heritability',
        'Rscript',
        script_fname,
        data_fname,
        result_fname,
        hash_fname,
        heritability_version,
        strain_data_fname)


with Popen(cmd, stdout=PIPE, stderr=PIPE, bufsize=1) as p, open(log_fname, 'ab') as file:
  for line in p.stdout: # b'\n'-separated lines
    logger.info(line) # pass bytes as is
    file.write(line)
  for line in p.stderr: # b'\n'-separated lines
    logger.error(sys.stdout.buffer.write(line)) # pass bytes as is
    
    
upload_blob_from_file(DATA_BUCKET, result_fname, result_blob)

