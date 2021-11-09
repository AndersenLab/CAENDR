# env

This directory contains the configuration details for each deployment environment. The variable definitions in the corresponding env directory are used both by Terraform for deploying infrastructure and in CAENDR's Python Modules. 

To define a deployment environment, include these files in the environment directory:
global.env
secret.env
backend.hcl

Examples:
secret.env.example
global.env.example
backend.hcl.example


.env files follow the standard formatting requirements for a bash environment file
Example
VARIABLE_NAME=value

The variable's name (VARIABLE_NAME) should be capitalized with words separated by underscores, followed by the assignment operator (=), then the value to be assigned (value) with no spaces in between.
Comments that start with '#' and blank lines are ignored.
To set an environment variable as false you must either remove it entirely or use '#' to comment out the line it's on, otherwise it will be set to the string value "false".

secret.env contains passwords and API keys that should NEVER be committed to the repository!

The 'admin' environment is unique and deploys a different, much smaller set of resources: primarily a cloud bucket acting as the Terraform backend for storing the state of each environment. 

The Terraform backend is configured for each environment in backend.hcl