# TODO: merge these definitions into Auth Service
USER_ROLES = [('user', 'User'), ('admin', 'Admin')]

class PRICES:
  DIVERGENT_SET = 160
  STRAIN_SET = 640
  STRAIN = 15
  SHIPPING = 65

JWT_LIMITED_TOKEN_EXPIRES = 15 * 60

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

REPORT_TYPES = [('V2', 'V2'), ('V1', 'V1'), ('V0', 'V0')]

# TODO: REMOVE THESE
REPORT_V1_FILE_LIST = ['methods.md']
REPORT_V2_FILE_LIST = ['alignment_report.html', 'concordance_report.html', 'gatk_report.html', 'methods.md', 'reads_mapped_by_strain.tsv', 'release_notes.md']
