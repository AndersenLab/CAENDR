# Parent Class & Models
from .job_pipeline           import JobPipeline
from caendr.models.datastore import GuideRNAReport

# Services
from caendr.models.status    import JobStatus
from caendr.utils.data       import get_object_hash



class GuideRNAPipeline(JobPipeline):

  #
  # Class variable assignments
  #

  # Managed class type assignments
  _Report_Class = GuideRNAReport
  _Task_Class   = None
  _Runner_Class = None

  # Type declarations for managed objects
  # This clues the type checker in to the specific subclasses we're using in this JobPipeline subclass
  report: _Report_Class


  # Temporary(?) override to intercept pipeline creation and mark the job as complete
  @classmethod
  def create(cls, *args, **kwargs):
    job = super().create(*args, **kwargs)
    if job.report.get_status() == JobStatus.CREATED:
      job.report.set_status(JobStatus.COMPLETE)
      job.report.save()
    return job


  #
  # Parsing Submission
  #

  @classmethod
  def parse(cls, data, valid_file_extensions=None):
    strains = ' '.join(sorted([ data.get('strain_1'), data.get('strain_2') or '-' ]))
    hash_source = f'{data["enzyme"]} {data["species"]} {strains} {data["site"]}'
    return {
      'props': data,
      'hash':  get_object_hash(hash_source, length=32),
    }



  #
  # Parsing Input
  #

  def _parse_input(self, data):
    return data



  #
  # Parsing Output
  #


  def _parse_output(self, data):
    return data



  #
  # Run Configuration
  #
  # These are required by the parent class, but this pipeline doesn't use a Runner,
  # so all functions can return empty values
  #

  def construct_command(self):
    return []

  def construct_environment(self):
    return {}

  def construct_run_params(self):
    return {}
