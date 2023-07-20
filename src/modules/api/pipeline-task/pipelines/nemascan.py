import os
import logging

from caendr.models.task import NemaScanTask
from caendr.models.datastore import NemascanMapping, Species
from caendr.services.nemascan_mapping import get_mapping
from caendr.services.cloud.lifesciences import start_pipeline
from caendr.models.lifesciences import ServiceAccount, VirtualMachine, Resources, Action, Pipeline, Request
from caendr.utils.json import get_json_from_class


GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUD_ZONE = os.environ.get('GOOGLE_CLOUD_ZONE')

MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')
MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME')
MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME')


sa_email = f"{MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"
pub_sub_topic = f'projects/{GOOGLE_CLOUD_PROJECT_ID}/topics/{MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME}'


SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
MACHINE_TYPE = 'n1-standard-1'
PREEMPTIBLE = False
ZONE = 'us-central1-a'
TIMEOUT = '86400s'
BOOT_IMAGE = 'projects/cos-cloud/global/images/family/cos-stable'
VOLUME_NAME = 'nf-pipeline-work'
LOCAL_WORK_PATH = '/workdir'
BOOT_DISK_SIZE_GB = 100
ENABLE_STACKDRIVER_MONITORING = True

COMMAND = 'nemascan-nxf.sh'


def start_nemascan_pipeline(task: NemaScanTask):
  pipeline_req = _generate_nemascan_pipeline_req(task)
  return start_pipeline(task.id, pipeline_req)


def _generate_nemascan_pipeline_req(task: NemaScanTask):
  m = NemascanMapping.get_ds(task.id, silent=False)
  image_uri = m.get_container().uri()

  trait_file = f"gs://{m.get_bucket_name()}/{m.get_data_blob_path()}"
  output_dir = f"gs://{m.get_bucket_name()}/{m.get_result_path()}"
  work_dir = f"gs://{MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME}/{m.data_hash}"
  data_dir = f"gs://{m.get_bucket_name()}/{m.get_input_data_path()}"
  google_project = GOOGLE_CLOUD_PROJECT_ID
  google_zone = GOOGLE_CLOUD_ZONE

  container_name = f"nemascan-{m.id}"
  environment = {
    "USERNAME": m.username if m.username else None,
    "EMAIL": m.email if m.email else None,
    "SPECIES": m.species,
    "VCF_VERSION": Species.get(m.species)['release_latest'],
    "TRAIT_FILE": trait_file,
    "OUTPUT_DIR": output_dir,
    "WORK_DIR": work_dir,
    "DATA_DIR": data_dir,
    "GOOGLE_PROJECT": google_project,
    "GOOGLE_ZONE": google_zone,
    "GOOGLE_SERVICE_ACCOUNT_EMAIL": sa_email
  }

  service_account = ServiceAccount(email=sa_email, scopes=SCOPES)
  virtual_machine = VirtualMachine(machine_type=MACHINE_TYPE, preemptible=PREEMPTIBLE, boot_disk_size_gb=BOOT_DISK_SIZE_GB, 
                                  boot_image=BOOT_IMAGE, enable_stackdriver_monitoring=ENABLE_STACKDRIVER_MONITORING, service_account=service_account)
  resources = Resources(virtual_machine=virtual_machine, zones=[ZONE])
  action = Action(always_run=False, block_external_network=False, commands=[COMMAND], container_name=container_name, disable_image_prefetch=False,
                  disable_standard_error_capture=False, enable_fuse=False, environment=environment, ignore_exit_status=False, image_uri=image_uri, 
                  publish_exposed_ports=False, run_in_background=False, timeout=TIMEOUT)
  pipeline = Pipeline(actions=[action], resources=resources, timeout=TIMEOUT)
  pipeline_req = Request(pipeline=pipeline, pub_sub_topic=pub_sub_topic)
  return pipeline_req
