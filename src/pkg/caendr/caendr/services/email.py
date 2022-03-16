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

ORDER_SUBMISSION_EMAIL = """
Thank you for your order. Please retain this email for your records.

Information regarding your purchase, including its tracking number is available here:

{base_url}/order/invoice/{invoice_hash}/

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

DONATE_SUBMISSION_EMAIL = """
Thank you for your donation of ${donation_amount}. Please retain this email for your records.

Information regarding your purchase, including its tracking number is available here:

{base_url}/order/{invoice_hash}/

"""

PASSWORD_RESET_EMAIL = """
Reset Password

A password reset was requested for your account ({email}). If you did not authorize this, you may ignore this email.

To continue with your password reset, click the link below and follow the prompts. This link will expire in 15 minutes.

{password_reset_link}
"""
