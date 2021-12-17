CAENDR
=============================================================================

`CAENDR` is the code used to run the [_Caenorhabditis elegans_ Natural Diversity Resource](https://www.elegansvariation.org) website.

To allow the application to write to the google sheet where orders are stored, you must add the Google Sheets service account as an editor for the sheet {ANDERSEN_LAB_ORDER_SHEET}:

{GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com

You must also add the google analytics service account user:
{GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com

Required manual bucket uploads
-------------------------------------------------------------------

MODULE_SITE_BUCKET_PRIVATE_NAME/NemaScan/bin
MODULE_SITE_BUCKET_PRIVATE_NAME/NemaScan/input_data
