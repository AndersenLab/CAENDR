import os
import json
import logging
import tabix
from caendr.services.logger import logger

from caendr.models.task import HeritabilityTask
from caendr.models.datastore import HeritabilityReport
from caendr.services.heritability_report import get_heritability_report
from caendr.services.cloud.lifesciences import start_pipeline
from caendr.models.lifesciences import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request


GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUD_ZONE = os.environ.get('GOOGLE_CLOUD_ZONE')

MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')
MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME')


sa_email = f"{MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"
pub_sub_topic = f'projects/{GOOGLE_CLOUD_PROJECT_ID}/topics/{MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME}'


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
  h = HeritabilityReport(task.id)
  
  image_uri = h.get_container().uri()
  container_commands = _get_container_commands(task.container_version)
  logger.debug(f"Using image: {image_uri} with commands: {container_commands}")

  # prepare args
  # VCF_VERSION = "20210121"
  VCF_VERSION = "20220216"
  GOOGLE_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT_ID", None)
  GOOGLE_ZONE = os.getenv("GOOGLE_CLOUD_ZONE", None)
  MODULE_SITE_BUCKET_PRIVATE_NAME = os.getenv("MODULE_SITE_BUCKET_PRIVATE_NAME", None)
  MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME = os.getenv("MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME", None)
  MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME = os.getenv("MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME", None)

  # validation
  if GOOGLE_PROJECT is None:
    raise Exception("Missing GOOGLE_PROJECT")
  if GOOGLE_ZONE is None:
    raise Exception("Missing GOOGLE_ZONE")
  if MODULE_SITE_BUCKET_PRIVATE_NAME is None:
    raise Exception("Missing MODULE_SITE_BUCKET_PRIVATE_NAME")
  if MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME is None:
    raise Exception("Missing MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME")
  if MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME is None:
    raise Exception("Missing MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME")


  # GOOGLE_SERVICE_ACCOUNT_EMAIL = "mti-caendr-service-account@mti-caendr.iam.gserviceaccount.com"
  TRAIT_FILE = f"gs://{MODULE_SITE_BUCKET_PRIVATE_NAME}/reports/heritability/{h.container_version}/{h.data_hash}/data.tsv"
  WORK_DIR   = f"gs://{MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME}/{h.data_hash}"
  DATA_DIR   = f"gs://{MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME}/heritability"
  OUTPUT_DIR = f"gs://{MODULE_SITE_BUCKET_PRIVATE_NAME}/reports/heritability/{h.container_version}/{h.data_hash}"


  # running container name. THis is NOT the image 
  container_name = f"heritability-{h.id}"
  environment = {
    "GOOGLE_SERVICE_ACCOUNT_EMAIL": sa_email,
    "GOOGLE_PROJECT": GOOGLE_PROJECT,
    "GOOGLE_ZONE": GOOGLE_ZONE,
    "VCF_VERSION": VCF_VERSION,
    "TRAIT_FILE": TRAIT_FILE,
    "WORK_DIR": WORK_DIR,
    "DATA_DIR": DATA_DIR,
    "OUTPUT_DIR": OUTPUT_DIR,
    "DATA_HASH": h.data_hash, 
    "SPECIES": h['species'], 
    "DATA_BUCKET": h.get_bucket_name(), 
    "DATA_BLOB_PATH": h.get_blob_path()}

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
