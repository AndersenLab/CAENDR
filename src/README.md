# src

This directory contains:
* `modules`: Directories containing source code, Dockerfiles, Makefiles, etc... for each Service Module.
    * [Site](modules/site/README.md)
    * [API Pipeline Tasks](modules/api/pipeline-task/README.md)
    * [Database Operations](modules/db_operations/README.md)
    * [Heritability](modules/heritability/README.md)
    * [Image Thumbnail Generator](modules/img_thumb_gen/README.md)
    * [Indel Primer](modules/indel_primer/README.md)

* `pkg`: The CAENDR python package which contains libraries for accessing cloud services, models defining CAENDR internal data, utility functions that are commonly reused, and service libraries for interacting with CAENDR data. Modules include the CAENDR package in addition to their requirements.txt file.
    * [pkg/caendr](pkg/caendr/README.md)
