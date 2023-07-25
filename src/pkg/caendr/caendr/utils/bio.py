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



def parse_chrom_interval(interval):
  '''
    Parse a string representing a chromosome interval into a dict.

    Args:
      interval (str): The interval string to parse.

    Returns:
      dict:
        - chrom (str): The chromosome
        - start (int): The start location
        - stop (int):  The stop location

    Raises:
      ValueError: If input is not a valid interval string.
  '''

  # Perform RegEx search on interval string
  match = re.search(CHROM_INTERVAL_REGEX, interval.replace(',',''))

  # If there was a match, parse the capture groups
  if match:
    return {
      'chrom': match.group(1),
      'start': int(match.group(2)),
      'stop':  int(match.group(3)),
    }

  # Otherwise, raise a ValueError
  raise ValueError(f'Invalid chromosome interval string: "{interval}"')


def parse_chrom_position(position):
  '''
    Parse a string representing a chromosome position into a dict.

    Args:
      position (str): The interval string to parse.

    Returns:
      dict:
        - chrom (str): The chromosome
        - pos (int):   The location

    Raises:
      ValueError: If input is not a valid position string.
  '''

  # Perform RegEx search on position string
  match = re.search(CHROM_POSITION_REGEX, position.replace(',',''))

  # If there was a match, parse the capture groups
  if match:
    return {
      'chrom': match.group(1),
      'pos':   int(match.group(2)),
    }

  # Otherwise, raise a ValueError
  raise ValueError(f'Invalid chromosome position string: "{position}"')
