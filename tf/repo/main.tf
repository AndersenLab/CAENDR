terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 4.0"
    }
  }
}

# Configure the GitHub Provider
provider "github" {
  token = "${var.github_vars.token}"
}

data "github_organization" "org_name" {
  name = "${var.github_vars.org_name}"
}

data "github_repository" "caendr_repo" {
  full_name = "AndersenLab/CAENDR"
}
