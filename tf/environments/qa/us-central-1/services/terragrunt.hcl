locals {
  # Automatically load environment-level variables
  environment_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))

  # Extract out common variables for reuse
  env = local.environment_vars.locals.environment
  project = local.environment_vars.locals.project
  OU = local.environment_vars.locals.OU
}

# Include all settings from the root terragrunt.hcl file
include {
  path = find_in_parent_folders()
}

terraform {
    source = "../../../../caendr/modules//services"
}

inputs = {
    env = local.env
}