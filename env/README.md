# env

This directory contains the configuration details for each deployment environment. The variable definitions in the corresponding env directory are used both by Terraform for deploying infrastructure and in CAENDR's Python Modules. 

To define a deployment environment, include these .env files in the environment directory:
global.env
secret.env

Example .env files are included in the template directory:
example/global.example.env 
example/secret.example.env

secret.env contains passwords and API keys that should NEVER be committed to the repository!

To set an environment variable as false you must either remove it entirely or use '#' to comment out the line it's on, otherwise it will get set to the string value "false".