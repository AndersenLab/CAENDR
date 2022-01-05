CAENDR
=============================================================================

`CAENDR` is the code used to run the [_Caenorhabditis elegans_ Natural Diversity Resource](https://www.elegansvariation.org) website. Setup requires `make` which can be installed in ubuntu with:

```bash
sudo apt-get update && sudo apt-get install build-essential
```

Makefile Help
-------------------------------------------------------------------

To list all available makefile targets and their descriptions in the current directory:

```bash
make
```

or

```bash
make help
```

Requirements
-------------------------------------------------------------------

To automatically install system package requirements for development and deployment in Ubuntu:

```bash
make configure
```

Setting the Environment
-------------------------------------------------------------------

To configure your local environment to use the correct cloud resources, you must set the default project and credentials for the Google Cloud SDK and define the 'ENV' environment variable:

```bash
gcloud init
gcloud auth login
gcloud auth application-default login
gcloud auth configure-docker
export ENV=development
```

Running modules locally
-------------------------------------------------------------------

If the module requires a connection to the Cloud SQL instance, you will need to keep the Google Cloud SQL proxy running in the background:

```bash
./cloud_sql_proxy -instances=${GOOGLE_CLOUD_PROJECT_ID}:${GOOGLE_CLOUD_REGION}:${MODULE_DB_OPERATIONS_INSTANCE_NAME} -dir=/cloudsql &
```

Then switch to a different terminal prompt and change to the module's src directory:

```bash
make run
```

Deployment (development environment)
-------------------------------------------------------------------

```bash
export ENV=development
make cloud-resource-plan
make cloud-resource-deploy
```

Website Requirements
-------------------------------------------------------------------

To allow the website to write to the google sheet where orders are recorded, you must add the Google Sheets service account as an editor for the sheet {ANDERSEN_LAB_ORDER_SHEET}:
{GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com

You must also add the google analytics service account user to the Google Analytics account to view the 'about/statistics' page:
{GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com

Initial Setup
-------------------------------------------------------------------

Create a new user and log in to the site. Once the account has been created, you can manually promote it to admin by editing the `user` entity in Google Cloud Datastore.

Containerized Tools (Nemascan, Heritability, Indel Primer)
-------------------------------------------------------------------

Before these tools can be used for the first time, the available container versions must be loaded from docker hub. Visiting the 'Tool Versions' page in the 'Admin' portal will import this data automatically:

`Admin -> Tool Versions`

SQL Database
-------------------------------------------------------------------

These steps describe how to add data to the strain sheet, load it into the site database, then load the strain data, wormbase gene information, and strain variant annotation data into the site's SQL database:

- `Admin -> Strain Sheet`: The google sheet linked here must be populated with the strain data that you want to load into the site's internal database.
- `Admin -> Database Operations`: click 'New Operation' then 'Rebuild strain table from Google Sheet'. (No other fields are required)
- `Admin -> Database Operations`: click 'New Operation' then 'Rebuild wormbase gene table from external sources' (Wormbase Version number required)
- `Admin -> Database Operations`: click 'New Operation' then 'Rebuild Strain Annotated Variant table from .csv.gz file' (Strain Variant Annotation Version number required). This operation expects the .csv.gz source file to already exist in the Cloud Bucket location described below.

Strain Variant Annotation
-------------------------------------------------------------------

The strain variant annotation data csv should be versioned with the date of the release having the format YYYYMMDD, compressed with gzip, and uploaded to:

`${MODULE_DB_OPERATIONS_BUCKET_NAME}/strain_variant_annotation/c_elegans/WI.strain-annotation.bcsq.YYYYMMDDD.csv.gz`

Release Files
-------------------------------------------------------------------

To add a Dataset Release to the site through the Admin panel, you will first have to upload the release files to:

`${MODULE_SITE_BUCKET_PUBLIC_NAME}/dataset_release/c_elegans/${RELEASE_VERSION}`

using the file and directory structure described in the [AndersenLab dry guide](https://andersenlab.org/dry-guide/2021-12-01/cendr/)

Strain Photos
-------------------------------------------------------------------

Strain photos should be named using the format `<strain>.jpg` and uploaded to a bucket where the img_thumb_gen module will automatically create thumbnails with the format `<strain>.thumb.jpeg`:

`${MODULE_SITE_BUCKET_PHOTOS_NAME}/c_elegans/<strain>.jpg` -> `${MODULE_SITE_BUCKET_PHOTOS_NAME}/c_elegans/<strain>.thumb.jpg`

BAM/BAI Files
-------------------------------------------------------------------

BAM and BAI files are stored in:

`${MODULE_SITE_BUCKET_PRIVATE_NAME}/bam/c_elegans/<strain>.bam`
`${MODULE_SITE_BUCKET_PRIVATE_NAME}/bam/c_elegans/<strain>.bam.bai`

Nemascan
-------------------------------------------------------------------

Nemascan requires species data to be manually uploaded to cloud storage to make it accessible to the pipeline:

`${MODULE_SITE_BUCKET_PRIVATE_NAME}/NemaScan/input_data`
