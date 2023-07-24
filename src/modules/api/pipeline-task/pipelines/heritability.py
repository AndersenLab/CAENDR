import json
from caendr.services.logger import logger

from caendr.models.task import HeritabilityTask
from caendr.models.datastore import HeritabilityReport, Species
from caendr.services.cloud.lifesciences import start_pipeline
from caendr.models.lifesciences import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.utils.env import get_env_var


# Project Environment Variables
GOOGLE_CLOUD_PROJECT_ID = get_env_var('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION     = get_env_var('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUD_ZONE       = get_env_var('GOOGLE_CLOUD_ZONE')

# Site Environment Variables
MODULE_SITE_BUCKET_PRIVATE_NAME = get_env_var("MODULE_SITE_BUCKET_PRIVATE_NAME")

# Module Environment Variables
SERVICE_ACCOUNT_NAME    = get_env_var('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')
PUB_SUB_TOPIC_NAME      = get_env_var('MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME')
WORK_BUCKET_NAME        = get_env_var("MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME")
DATA_BUCKET_NAME        = get_env_var("MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME")


sa_email = f"{SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"
pub_sub_topic = f'projects/{GOOGLE_CLOUD_PROJECT_ID}/topics/{PUB_SUB_TOPIC_NAME}'


# Job Parameters
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
MACHINE_TYPE = 'n1-standard-1'
PREEMPTIBLE = False
ZONE = 'us-central1-a'
TIMEOUT = '9000s'
BOOT_IMAGE = 'projects/cos-cloud/global/images/family/cos-stable'
VOLUME_NAME = 'nf-pipeline-work'
LOCAL_WORK_PATH = '/workdir'
BOOT_DISK_SIZE_GB = 10
ENABLE_STACKDRIVER_MONITORING = True

# Override the entry point for the container based on the version. 
# The container v0.3 is built from: https://github.com/AndersenLab/calc_heritability
# The container v0.1a is built from: https://github.com/AndersenLab/CAENDR/tree/development/src/modules/heritability
def _get_container_commands(version):
  if version == "v0.1a":
    return ['python', '/h2/main.py']
  return ["./heritability-nxf.sh"]
      
# COMMANDS = ['python', '/h2/main.py']
# COMMANDS = ['/heritability/heritability-nxf.sh']

def start_heritability_pipeline(task: HeritabilityTask):
  pipeline_req = _generate_heritability_pipeline_req(task)
  return start_pipeline(task.id, pipeline_req)


def _generate_heritability_pipeline_req(task: HeritabilityTask):
  h = HeritabilityReport.get_ds(task.id, silent=False)
  
  image_uri = h.get_container().uri()
  TRAIT_FILE = f"gs://{MODULE_SITE_BUCKET_PRIVATE_NAME}/reports/heritability/{h.container_version}/{h.data_hash}/data.tsv"
  WORK_DIR   = f"gs://{WORK_BUCKET_NAME}/{h.data_hash}"
  DATA_DIR   = f"gs://{DATA_BUCKET_NAME}/heritability"
  OUTPUT_DIR = f"gs://{MODULE_SITE_BUCKET_PRIVATE_NAME}/reports/heritability/{h.container_version}/{h.data_hash}"

  # running container name. THis is NOT the image 
  container_name = f"heritability-{h.id}"
  environment = {
    "GOOGLE_SERVICE_ACCOUNT_EMAIL": sa_email,
    "GOOGLE_PROJECT": GOOGLE_CLOUD_PROJECT_ID,
    "GOOGLE_ZONE": GOOGLE_CLOUD_ZONE,
    "VCF_VERSION": Species.get(h.species)['release_latest'],
    "TRAIT_FILE": TRAIT_FILE,
    "WORK_DIR": WORK_DIR,
    "DATA_DIR": DATA_DIR,
    "OUTPUT_DIR": OUTPUT_DIR,
    "DATA_HASH": h.data_hash,
    "SPECIES": h['species'],
    "DATA_BUCKET": h.get_bucket_name(),
    "DATA_BLOB_PATH": h.get_blob_path(),
  }

  container_commands = _get_container_commands(task.container_version)
  logger.debug(f"Using image: {image_uri} with commands: {container_commands}")
  logger.debug(f"Environment: { json.dumps(environment) }")

  service_account = ServiceAccount(email=sa_email, scopes=SCOPES)
  virtual_machine = VirtualMachine(machine_type=MACHINE_TYPE,
                                  preemptible=PREEMPTIBLE,
                                  boot_disk_size_gb=BOOT_DISK_SIZE_GB,
                                  boot_image=BOOT_IMAGE, enable_stackdriver_monitoring=ENABLE_STACKDRIVER_MONITORING, service_account=service_account)
  resources = Resources(virtual_machine=virtual_machine, zones=[ZONE])
  action = Action(always_run=False, block_external_network=False, commands=container_commands, container_name=container_name, disable_image_prefetch=False,
                  disable_standard_error_capture=False, enable_fuse=False, environment=environment, ignore_exit_status=False, image_uri=image_uri, 
                  publish_exposed_ports=False, run_in_background=False, timeout=TIMEOUT)
  pipeline = Pipeline(actions=[action], resources=resources, timeout=TIMEOUT)
  pipeline_req = Request(pipeline=pipeline, pub_sub_topic=pub_sub_topic)
  return pipeline_req
