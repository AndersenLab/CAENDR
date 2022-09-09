# CAENDR

`CAENDR` is the code used to run the [_Caenorhabditis elegans_ Natural Diversity Resource](https://www.elegansvariation.org) website. 

## GCP Credentials

Ask in MS teams for the DevOps service-account json file. Create a local folder under your home directory named ~/.gcp and copy the service account json file to that folder.
```
$ mkdir ~/.gcp
open -a Finder ~/.gcp 
```
The last line should open MacOS Finder on the `~/.gcp/` folder. Drop the `.json` service account file there. 

## MacOS setup

*Requirements*

* Docker Mac (https://docs.docker.com/desktop/install/mac-install/) 
* homebrew (install from https://brew.sh/)

Steps:
```
brew update
brew install python-devel
brew install pyenv
```

Edit your `~/.bash_profile` and add this to the bottom of the file. If the file doens't exist, create a new one. 

```
# if using bash, do 
nano ~/.bash_profile
# if using zsh then 
nano ~/.zprofile

export PATH=$HOME/.pyenv/bin:$PATH
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# if using bash, do 
source ~/.bash_profile
# if using zsh then 
source ~/.zprofile
```

# pyenv
export PATH=$HOME/.pyenv/bin:$PATH
eval "$(pyenv init --path)"
eval "$(pyenv init -)"


pyenv install 3.7.12
pyenv global 3.7.12
pip install virtualenv
``` 

Expected Outputs:

```
$ python -V
Python 3.7.12
```

## Running local (work-in-progress)

Open one terminal window and run:
```
export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/NAME_OF_THE_SERVICE_ACCOUNT_FILE.json
export ENV=main
cd src/modules/site
make clean
make configure
make cloud-sql-proxy-start
```

Open a second terminal window:
```
export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/NAME_OF_THE_SERVICE_ACCOUNT_FILE.json
export ENV=main
cd src/modules/site
make run
```


## Linux Setup
Setup requires `make` which can be installed with:

```bash
sudo apt-get update && sudo apt-get install build-essential
```

## Makefile Help
-------------------------------------------------------------------
To list all available MakeFile targets and their descriptions in the current directory:

```bash
make
```

or

```bash
make help
```

## Requirements
-------------------------------------------------------------------
To automatically install system package requirements for development and deployment:

```bash
make configure
```

## Setting the Environment and gcloud login
-------------------------------------------------------------------
To configure your local environment to use the correct cloud resources, you must set the default project and credentials for the Google Cloud SDK and define the 'ENV' environment variable:

```bash
gcloud init
gcloud auth login
gcloud auth application-default login
gcloud auth configure-docker
export ENV={ENV_TO_DEPLOY}
```

## Running modules locally
-------------------------------------------------------------------
Set ENV and GOOGLE_APPLICATION_CREDENTIALS environment variables:
```bash
export MODULE_DB_OPERATIONS_CONNECTION_TYPE=localhost
export MODULE_DB_TIMEOUT=3
export ENV={ENV_TO_DEPLOY}
export GOOGLE_APPLICATION_CREDENTIALS={PATH_TO_GCP_CREDENTIALS}
```

If the module requires a connection to the Cloud SQL instance, you will need to keep the [Google Cloud SQL proxy](https://cloud.google.com/sql/docs/mysql/quickstart-proxy-test#macos-64-bit) running in the background:
```bash
./cloud_sql_proxy -instances=${GOOGLE_CLOUD_PROJECT_ID}:${GOOGLE_CLOUD_REGION}:${MODULE_DB_OPERATIONS_INSTANCE_NAME} -dir=/cloudsql &
```
or
```bash
make cloud-sql-proxy-start
```

Then switch to a different terminal prompt and change to the module's src directory:
```bash
make run
```

## Deployment of Individual Components
-------------------------------------------------------------------
Directions for deploying each module:
* [Site](src/modules/api/pipeline-task/README.md)
* [API Pipeline Tasks](src/modules/api/pipeline-task/README.md)
* [Database Operations](src/modules/db_operations/README.md)
* [Gene Browser Tracks](src/modules/gene_browser_tracks/README.md)
* [Heritability](src/modules/heritability/README.md)
* [Image Thumbnail Generator](src/modules/img_thumb_gen/README.md)
* [Indel Primer](src/modules/indel_primer/README.md)

Troubleshooting:
* Even if ENV and GOOGLE_APPLICATION_CREDENTIALS are set correctly you will need to be [logged into gcloud and configure docker](#setting-the-environment-and-gcloud-login) to enable publishing containers to GCR since the service account does not have permissions to publish.

##  Website Requirements
-------------------------------------------------------------------
To allow the website to write to the google sheet where orders are recorded, you must add the Google Sheets service account as an editor for the sheet {ANDERSEN_LAB_ORDER_SHEET}:
{GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com

You must also add the google analytics service account user to the Google Analytics account to view the 'about/statistics' page:
{GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com

## Initial Setup
-------------------------------------------------------------------
Create a new user and log in to the site. Once the account has been created, you can manually promote it to admin by editing the `user` entity in Google Cloud Datastore.

## Containerized Tools (Nemascan, Heritability, Indel Primer)
-------------------------------------------------------------------
Before these tools can be used for the first time, the available container versions must be loaded from docker hub. Visiting the 'Tool Versions' page in the 'Admin' portal will import this data automatically:

`Admin -> Tool Versions`

## SQL Database
-------------------------------------------------------------------
These steps describe how to add data to the strain sheet, load it into the site database, then load the strain data, wormbase gene information, and strain variant annotation data into the site's SQL database:

- `Admin -> Strain Sheet`: The google sheet linked here must be populated with the strain data that you want to load into the site's internal database.
- `Admin -> Database Operations`: click 'New Operation' then 'Rebuild strain table from Google Sheet'. (No other fields are required)
- `Admin -> Database Operations`: click 'New Operation' then 'Rebuild wormbase gene table from external sources' (Wormbase Version number required)
- `Admin -> Database Operations`: click 'New Operation' then 'Rebuild Strain Annotated Variant table from .csv.gz file' (Strain Variant Annotation Version number required). This operation expects the .csv.gz source file to already exist in the Cloud Bucket location described below.

## ##Strain Variant Annotation
-------------------------------------------------------------------
The strain variant annotation data csv should be versioned with the date of the release having the format YYYYMMDD, compressed with gzip, and uploaded to:

`${MODULE_DB_OPERATIONS_BUCKET_NAME}/strain_variant_annotation/c_elegans/WI.strain-annotation.bcsq.YYYYMMDDD.csv.gz`

## Release Files
-------------------------------------------------------------------
To add a Dataset Release to the site through the Admin panel, you will first have to upload the release files to:

`${MODULE_SITE_BUCKET_PUBLIC_NAME}/dataset_release/c_elegans/${RELEASE_VERSION}`

using the file and directory structure described in the [AndersenLab dry guide](https://andersenlab.org/dry-guide/2021-12-01/cendr/)

## Strain Photos
-------------------------------------------------------------------
Strain photos should be named using the format `<strain>.jpg` and uploaded to a bucket where the img_thumb_gen module will automatically create thumbnails with the format `<strain>.thumb.jpeg`:

`${MODULE_SITE_BUCKET_PHOTOS_NAME}/c_elegans/<strain>.jpg` -> `${MODULE_SITE_BUCKET_PHOTOS_NAME}/c_elegans/<strain>.thumb.jpg`

## BAM/BAI Files
-------------------------------------------------------------------
BAM and BAI files are stored in:

`${MODULE_SITE_BUCKET_PRIVATE_NAME}/bam/c_elegans/<strain>.bam`
`${MODULE_SITE_BUCKET_PRIVATE_NAME}/bam/c_elegans/<strain>.bam.bai`

## Nemascan
-------------------------------------------------------------------
Nemascan requires species data to be manually uploaded to cloud storage to make it accessible to the pipeline:

`${MODULE_SITE_BUCKET_PRIVATE_NAME}/NemaScan/input_data`

## FAQ
-------------------------------------------------------------------
Q: Why does it look like the `site` or `db_operations` are unable to connect to Cloud SQL (PostGres)?
A: Check if the server exhausted the `max_connections` limit. Google Postgres has a hard limit on connections and there is a reserved number of connections for super-admin (backups, etc), that are not available for run-time apps/services/modules. Consider restarting (or stopping and starting) to close all the active connections. In GCP this can be viewed in the POSTGRES tab, select the "Active Connections" from the dropdown to view the stats.
