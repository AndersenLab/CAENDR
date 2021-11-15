SITE Module - src/modules/site
=============================================================================



The site module is an App Engine Flex container which uses Gunicorn as the Python WSGI HTTP Server (Web Server Gateway Interface) and Flask as the web framework and Jinja as the HTML template engine. 

User data and site configuration properties are stored as Datastore Entities in Google Cloud. 

Gene and strain data is stored in a CloudSQL Postgres database that is initially empty after provisioning by Terraform. 

There is still a significant number of files that must be added manually (ie: BAM/BAI, Gene tracks, etc..)

