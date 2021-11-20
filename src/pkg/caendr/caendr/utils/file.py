import os
import hashlib
import urllib.request as request
import shutil

from contextlib import closing
from logzero import logger


def get_dir_list_sorted(path):
  """ returns a sorted list of the directory contents at the os path argument  """
  return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse=True)


def get_file_hash(filename, length=10):
  ''' Generates the sha1 hash of a file's contents and returns the first 'length' characters '''
  logger.debug(filename)
  BLOCKSIZE = 65536
  hasher = hashlib.sha1()
  with open(filename, 'rb') as afile:
    buf = afile.read(BLOCKSIZE)
    while len(buf) > 0:
      hasher.update(buf)
      buf = afile.read(BLOCKSIZE)
  
  return hasher.hexdigest()[0:length]


def download_file(url: str, fname: str):
  '''
    download_file [Downloads a file as a stream to minimize resources]
      Args:
        url (str): [URL of the file to be downloaded]
        fname (str): [The local filename given to the downloaded file]
      Returns:
        (str): [The local filename given to the downloaded file]
  '''  
  with closing(request.urlopen(url)) as r:
    with open(fname, 'wb') as f:
      shutil.copyfileobj(r, f)

  return fname
