import json

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import IndelPrimerReport
from caendr.models.run             import IndelPrimerRunner
from caendr.models.task            import IndelPrimerTask

# Services
from caendr.models.datastore       import Species
from caendr.utils.data             import get_object_hash
from caendr.utils.env              import get_env_var


INDEL_PRIMER_CONTAINER_NAME = get_env_var('INDEL_PRIMER_CONTAINER_NAME')



class IndelFinderPipeline(JobPipeline):

  _Report_Class = IndelPrimerReport
  _Task_Class   = IndelPrimerTask
  _Runner_Class = IndelPrimerRunner

  _Container_Name = INDEL_PRIMER_CONTAINER_NAME


  #
  # Parsing
  #

  @classmethod
  def parse(cls, data, valid_file_extensions=None):
    data_file = json.dumps(data)
    data_hash = get_object_hash(data, length=32)

    # TODO: Pull this value from somewhere
    release = Species.from_name( data['species'] ).release_pif

    # Add release information to data object
    data.update({
      'release':         release,
      'sv_bed_filename': IndelPrimerReport.get_source_filename(data['species'], release) + '.bed.gz',
      'sv_vcf_filename': IndelPrimerReport.get_source_filename(data['species'], release) + '.vcf.gz',
    })

    return {
      'props': data,
      'hash':  data_hash,
      'files': [data_file],
    }
