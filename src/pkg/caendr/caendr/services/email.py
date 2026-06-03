import requests
from caendr.services.cloud.secret import get_secret

MAILGUN_API_KEY = get_secret('MAILGUN_API_KEY')

def send_email(data):
  ''' Send an email using Mailgun API '''
  return requests.post(
    "https://api.mailgun.net/v3/mail.elegansvariation.org/messages",
    auth=("api", MAILGUN_API_KEY),
    data=data
  )


MAPPING_SUBMISSION_EMAIL = """
You have submitted a genome-wide association mapping to CeNDR successfully.
You can monitor progress of your report here:

{base_url}/report/{report_slug}/

If you set your record to private, this email serves as a way for you to find the URL to your report. 

"""

ORDER_SUBMISSION_EMAIL_TEMPLATE = """
Thank you for your order. Please retain this email for your records.

Information regarding your purchase, including its tracking number is available here:

{order_confirmation_link}

Address
=======
{name}
{address}

Items
=====
{items}

Total
=====
{total}

Date
====
{date}

"""

DONATION_SUBMISSION_EMAIL_TEMPLATE = """
Thank you for your donation of ${donation_amount}. Please retain this email for your records.

Information regarding your purchase, including its tracking number is available here:

{order_confirmation_link}

"""

PASSWORD_RESET_EMAIL_TEMPLATE = """
Reset Password

A password reset was requested for your account ({email}). If you did not authorize this, you may ignore this email.

To continue with your password reset, click the link below and follow the prompts. This link will expire in 24 hours and can only be used one time.

{password_reset_magic_link}
"""

REPORT_SUCCESS_EMAIL_TEMPLATE = """
Your {report_type} report is now complete.
You may access your report here:

{report_link}
"""

REPORT_ERROR_EMAIL_TEMPLATE = """
We're sorry, but there was an error processing your {report_type} report.
You may find more information here:

{report_link}
"""



#
# Trait Submission (Users)
#

TRAIT_REVIEW_SUBMIT_EMAIL_TEMPLATE_USER = """
Hello CaeNDR user,

Thank you for your new trait submission! We will review the trait description and data format before release. Please expect emails from CaeNDR with questions or approval.

Thank you,
Erik
"""

TRAIT_REVIEW_ACCEPT_EMAIL_TEMPLATE_USER = """
Hello CaeNDR user,

Your new trait submission has passed QC and will be released on CaeNDR soon.

Thank you,
Erik
"""

# TRAIT_REVIEW_REJECT_EMAIL_TEMPLATE_USER = """
# Your trait has been rejected.

# Trait:
# {trait_name}
# """

TRAIT_REVIEW_RETRACT_EMAIL_TEMPLATE_USER = """
Hello CaeNDR user,

You have removed your trait from the public CaeNDR database.

Thank you,
Erik
"""

# TRAIT_REVIEW_RETRACT_EMAIL_TEMPLATE_AFFECTED_USERS = """
# A trait you have used in a report has been retracted.

# Trait:
# {trait_name}
# """



#
# Trait Submission (Admins)
#

TRAIT_REVIEW_SUBMIT_EMAIL_TEMPLATE_ADMIN = """
A new trait has been submitted.

Trait:
{trait_name}

User:
{user_name}

{review_link}
"""

# TRAIT_REVIEW_RETRACT_EMAIL_TEMPLATE_ADMIN = """
# A trait in the Phenotype Database has been retracted.

# Trait:
# {trait_name}

# User:
# {user_name}
# """
