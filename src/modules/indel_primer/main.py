import os
import sys

from subprocess import Popen, PIPE, STDOUT
from logzero import logger
from dotenv import load_dotenv

from caendr.models.error import EnvVarError
from caendr.services.cloud.storage import upload_blob_from_file

dotenv_file = '.env'
load_dotenv(dotenv_file)

MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')

INDEL_SITE = os.environ.get('INDEL_SITE')
INDEL_STRAIN_1 = os.environ.get('INDEL_STRAIN_1')
INDEL_STRAIN_2 = os.environ.get('INDEL_STRAIN_2')
RESULT_BUCKET = os.environ.get('RESULT_BUCKET')
RESULT_BLOB = os.environ.get('RESULT_BLOB')

WORMBASE_VERSION = os.environ.get('WORMBASE_VERSION')
INDEL_VCF_VERSION = os.environ.get('INDEL_VCF_VERSION')


logger.info(f'Indel Primer: INDEL_SITE:{INDEL_SITE} INDEL_STRAIN_1:{INDEL_STRAIN_1} INDEL_STRAIN_2:{INDEL_STRAIN_2} WORMBASE_VERSION:{WORMBASE_VERSION} INDEL_VCF_VERSION:{INDEL_VCF_VERSION} RESULT_BUCKET:{RESULT_BUCKET} RESULT_BLOB:{RESULT_BLOB}')

if not INDEL_SITE or not INDEL_STRAIN_1 or not INDEL_STRAIN_2 or not RESULT_BLOB or not RESULT_BUCKET or not WORMBASE_VERSION or not INDEL_VCF_VERSION:
  raise EnvVarError()


cmd = ('conda', 
        'run',
        '-n',
        'indel-primer',
        'vk',
        'primer',
        'indel',
        '--region',
        INDEL_SITE,
        '--nprimers',
        '10',
        '--polymorphic',
        '--ref',
        WORMBASE_VERSION,
        '--samples',
        f'{INDEL_STRAIN_1},{INDEL_STRAIN_2}', INDEL_VCF_VERSION)


with Popen(cmd, stdout=PIPE, stderr=PIPE, bufsize=1) as p, open('results.tsv', 'ab') as file:
  for line in p.stdout: # b'\n'-separated lines
    logger.info(line) # pass bytes as is
    file.write(line)
  for line in p.stderr: # b'\n'-separated lines
    logger.error(sys.stdout.buffer.write(line)) # pass bytes as is

upload_blob_from_file(RESULT_BUCKET, 'results.tsv', RESULT_BLOB)

