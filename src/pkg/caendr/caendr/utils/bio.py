from caendr.utils.constants import CHROM_ARM_CENTER


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
