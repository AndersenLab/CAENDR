# Maps chromosome in roman numerals to integer
CHROM_NUMERIC = {
  "I": 1,
  "II": 2,
  "III": 3,
  "IV": 4,
  "V": 5,
  "X": 6,
  "MtDNA": 7 
}


BIOTYPES = {
  "miRNA": "microRNA",
  "piRNA": "piwi-interacting RNA",
  "rRNA": "ribosomal RNA",
  "siRNA": "small interfering RNA",
  "snRNA": "small nuclear RNA",
  "snoRNA": "small nucleolar RNA",
  "tRNA": "transfer RNA",
  "vaultRNA": "Short non-coding RNA genes that form part of the vault ribonucleoprotein complex",
  "lncRNA": "Long non-coding RNA",
  "lincRNA": "Long interspersed ncRNA",
  "pseudogene": "non-functional gene.",
  "asRNA": "Anti-sense RNA",
  "ncRNA": "Non-coding RNA",
  "scRNA": "Small cytoplasmic RNA"
}

# chrom : left tip, left arm, center, right arm, right tip
# From Rockman Krugylak 2009
CHROM_ARM_CENTER = {'I': (527, 3331, 7182, 3835, 197),
                    'II': (306, 4573, 7141, 2589, 670),
                    'III': (494, 3228, 6618, 2877, 567),
                    'IV': (720, 3176, 9074, 3742, 782),
                    'V': (643, 5254, 10653, 3787, 583),
                    'X': (572, 5565, 6343, 3937, 1302)}


STRAIN_NAME_REGEX    = "([A-Z]+)([0-9]+)"
CHROM_INTERVAL_REGEX = "^(I|II|III|IV|V|X|MtDNA):([0-9,]+)-([0-9,]+)$"
CHROM_POSITION_REGEX = "^(I|II|III|IV|V|X|MtDNA):([0-9,]+)$"


# Max number of rows to insert into a SQL table in a single commit
DEFAULT_BATCH_SIZE = 100000
