from diagrams import Cluster, Diagram
from diagrams.gcp.storage import Storage
from diagrams.gcp.database import Datastore
from diagrams.gcp.analytics import Genomics 
from diagrams.gcp.compute import ComputeEngine, Run
from diagrams.gcp.devtools import Tasks
from diagrams.gcp.analytics import PubSub

with Diagram('Pipeline Task Execution', show=True):
  nscalc_queue = Tasks('Task Queue: ns_calc')
  report_bucket = Storage('gs://elegansvariation.org/reports/nemascan/')
  pipeline_task_api = Run('Pipeline Task API')

  with Cluster('Pipeline Status'):
    nscalc_pubsub = PubSub('PubSub: nemascan')
    nscalc_ds = Datastore('Datastore: ns_calc')
    gls_op_ds = Datastore('Datastore: gls_operation')

  with Cluster('Nemascan Pipeline'):
    pipeline = Genomics('nemascan-nxf\ncontainer')
    input_data_bucket = Storage('gs://nf-pipelines/NemaScan/input_data')
    work_bucket = Storage('gs://nf-pipelines/workdir')

    with Cluster('Pipeline Workers'):
      worker1 = ComputeEngine('nemascan-worker\ncontainer')
      worker2 = ComputeEngine('nemascan-worker\ncontainer')
      worker3 = ComputeEngine('nemascan-worker\ncontainer')
      worker4 = ComputeEngine('nemascan-worker\ncontainer')
      worker5 = ComputeEngine('nemascan-worker\ncontainer')

    workers = [worker1, worker2, worker3, worker4, worker5]

  nscalc_queue >> pipeline_task_api >> pipeline

  pipeline >> nscalc_pubsub
  nscalc_pubsub >> pipeline_task_api
  pipeline >> workers 
  pipeline << workers
  workers >> work_bucket
  workers << work_bucket
  input_data_bucket >> worker1
  worker5 >> report_bucket
  pipeline_task_api >> gls_op_ds
  pipeline_task_api >> nscalc_ds



