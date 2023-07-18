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



def parse_interval_query(query):

  # Perform RegEx search on query string
  match = re.search(CHROM_INTERVAL_REGEX, query.replace(',',''))

  # If there was a match, parse the capture groups
  if match:
    return {
      'chrom': match.group(1),
      'start': int(match.group(2)),
      'stop':  int(match.group(3)),
    }


def parse_position_query(query):

  # Perform RegEx search on query string
  match = re.search(CHROM_POSITION_REGEX, query.replace(',',''))

  # If there was a match, parse the capture groups
  if match:
    return {
      'chrom': match.group(1),
      'pos':   int(match.group(2)),
    }
