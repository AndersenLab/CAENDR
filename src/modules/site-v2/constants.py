# TODO: merge these definitions into Auth Service
USER_ROLES = [('user', 'User'), ('admin', 'Admin')]

class PRICES:
  DIVERGENT_SET = 160
  STRAIN_SET = 640
  STRAIN = 15
  SHIPPING = 65

SECTOR_OPTIONS = [
  ('academia', 'Academia'),
  ('industry', 'Industry')
]

SHIPPING_OPTIONS = [
  ('UPS', 'UPS'),
  ('FEDEX', 'FEDEX'),
  ('Flat Rate Shipping', '${} Flat Fee'.format(PRICES.SHIPPING))
]

PAYMENT_OPTIONS = [
  ('check', 'Check'),
  ('credit_card', 'Credit Card')
]

TABLE_COLORS = {
  "LOW": 'success',
  "MODERATE": 'warning',
  "HIGH": 'danger'
}

# TODO: REMOVE THESE
REPORT_V1_FILE_LIST = ['methods.md']
REPORT_V2_FILE_LIST = ['alignment_report.html', 'concordance_report.html', 'gatk_report.html', 'methods.md', 'reads_mapped_by_strain.tsv', 'release_notes.md']


# TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS = { 'csv', 'tsv' }
# TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS = { 'csv' }
TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS = { 'tsv' }

TRAIT_CATEGORY_OPTIONS = [('1', 'Growth/Physiology'), ('2', 'Morphology/Development/Lineage/Cell type'), ('3', 'Behavior'), ('4', 'Molecular'), ('5', 'Stress response'), ('6', 'Drug/Compound/Condition/Treatment'), ('7', 'Ecology'), ('8', 'Genomics'), ('9', 'Reproduction')]
