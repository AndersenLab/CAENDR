import gzip
import os
import hashlib
import urllib.request as request
import shutil

from contextlib import closing
from caendr.services.logger import logger


def get_dir_list_sorted(path):
  """ returns a sorted list of the directory contents at the os path argument  """
  return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse=True)


def get_file_hash(path_or_file: os.PathLike, length=10):
  '''
    Generates the sha1 hash of a file's contents and returns the first 'length' characters.
  '''
  logger.debug(path_or_file)
  BLOCKSIZE = 65536
  hasher = hashlib.sha1()
  with open(path_or_file, 'rb') as afile:
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

def write_string_to_file(data: str, fname: str):
  textfile = open(fname, "w")
  a = textfile.write(data)
  textfile.close()



def unzip_gz(gz_fname: str, keep_zipped_file: bool = False):
  '''
    Unzip a GZIP (`.gz`) file.

    Arguments:
      - gz_fname (str):
          The name of the file to unzip.
      - keep_zipped_file (bool, optional):
          Whether to keep the original `.gz` file after it has been unzipped (`True`) or remove it (`False`).
          Defaults to `False`.

    Returns:
      The name of the unzipped file.
  '''

  # Generate a name for the unzipped file
  if gz_fname[-3:] == '.gz':
    fname = gz_fname[:-3]
    using_tempname = False
  else:
    fname = f'{gz_fname}_UNZIPPED'
    using_tempname = True

  # Unzip the .gz file and copy its contents to the new unzipped file
  with gzip.open(gz_fname, 'rb') as f_in:
    with open(fname, 'wb') as f_out:
      shutil.copyfileobj(f_in, f_out)

  # Optionally delete the zipped file
  if not keep_zipped_file:
    os.remove(gz_fname)

    # If we had to append '_UNZIPPED' to avoid a name collision, but we're only keeping the unzipped file,
    # we can rename the new unzipped file to keep the original name
    if using_tempname:
      os.rename(fname, gz_fname)
      fname = gz_fname

  # Return the name of the new unzipped file
  return fname
