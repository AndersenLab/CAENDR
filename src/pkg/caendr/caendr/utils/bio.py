import re

from caendr.utils.constants import CHROM_ARM_CENTER, CHROM_INTERVAL_REGEX, CHROM_POSITION_REGEX



def arm_or_center(chrom, pos):
  """
      Determines whether a position is on the
      arm or center of a chromosome.
  """
  if chrom == 'MtDNA':
      return None
  ca = CHROM_ARM_CENTER[chrom]
  ca = [x * 1000 for x in ca]
  c = 'arm'
  if pos > ca[1]:
      c = 'center'
  if pos > ca[2]:
      c = 'arm'
  return c



def parse_interval_query(query, silent=True):
  '''
    Parse a string representing a chromosome interval into a dict.

    Args:
      query (str): The interval string to parse.
      silent (bool, optional): If False, throw a ValueError if the query is not a valid interval. If True, returns None instead. Default True.

    Returns:
      dict:
        - chrom (str): The chromosome
        - start (int): The start location
        - stop (int):  The stop location
  '''

  # Perform RegEx search on query string
  match = re.search(CHROM_INTERVAL_REGEX, query.replace(',',''))

  # If there was a match, parse the capture groups
  if match:
    return {
      'chrom': match.group(1),
      'start': int(match.group(2)),
      'stop':  int(match.group(3)),
    }

  if not silent:
    raise ValueError(f'Invalid interval query string: {query}')


def parse_position_query(query, silent=True):
  '''
    Parse a string representing a chromosome position into a dict.

    Args:
      query (str): The interval string to parse.
      silent (bool, optional): If False, throw a ValueError if the query is not a valid position. If True, returns None instead. Default True.

    Returns:
      dict:
        - chrom (str): The chromosome
        - pos (int):   The location
  '''

  # Perform RegEx search on query string
  match = re.search(CHROM_POSITION_REGEX, query.replace(',',''))

  # If there was a match, parse the capture groups
  if match:
    return {
      'chrom': match.group(1),
      'pos':   int(match.group(2)),
    }

  if not silent:
    raise ValueError(f'Invalid position query string: {query}')
