# CAENDR

`CAENDR` is the code used to run the [_Caenorhabditis elegans_ Natural Diversity Resource](https://www.elegansvariation.org) website.



To allow the application to write to the google sheet where orders are stored, you must add the Google Sheets service account as an editor for the sheet {CENDR_PUBLICATIONS_SHEET}:
{GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com
