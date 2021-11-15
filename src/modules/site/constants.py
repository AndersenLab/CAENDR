
USER_ROLES = [('user', 'User'), ('admin', 'Admin')]
GOOGLE_SHEET_PREFIX = "https://docs.google.com/spreadsheets/d"

class PRICES:
  DIVERGENT_SET = 160
  STRAIN_SET = 640
  STRAIN = 15
  SHIPPING = 65

SHIPPING_OPTIONS = [
  ('UPS', 'UPS'),
  ('FEDEX', 'FEDEX'),
  ('Flat Rate Shipping', '${} Flat Fee'.format(PRICES.SHIPPING))
]

PAYMENT_OPTIONS = [
  ('check', 'Check'),
  ('credit_card', 'Credit Card')
]

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

TABLE_COLORS = {
  "LOW": 'success',
  "MODERATE": 'warning',
  "HIGH": 'danger'
}

REPORT_VERSIONS = ['', 'v1', 'v2']
REPORT_V1_FILE_LIST = ['methods.md']
REPORT_V2_FILE_LIST = ['alignment_report.html', 'concordance_report.html', 'gatk_report.html', 'methods.md', 'reads_mapped_by_strain.tsv', 'release_notes.md']
