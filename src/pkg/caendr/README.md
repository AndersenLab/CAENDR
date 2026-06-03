# CAENDR Python Package
## src/pkg/caendr
-------------------------------------------------------------------
This directory contains the CAENDR python package. Installation requirements and version details are defined in setup.py

=============================================================================

## Features
-------------------------------------------------------------------
- `models` - data model classes
- `models.sql` - SQLAlchemy Object Relational Model classes
- `models.datastore` - Datastore Entity classes
- `services` - interacting with CAENDR resources
- `services.cloud` - lower-level interaction directly with Google Cloud resources
- `utils` - commonly used functions


## Best Practices

### Environment Variables
To read in environment variables, use the `load_env` and `get_env_var` functions from `utils.env`:
- Track whether an environment is loaded, and throw a more descriptive error if the code tries to load a variable before any environment is loaded
- Handle missing environment variables and default values
- Handle template strings
