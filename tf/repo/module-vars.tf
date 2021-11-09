locals {

  github_vars = tomap({
    "repo_name" = "${var.GITHUB_REPO_NAME}",
    "org_name" = "${var.GITHUB_ORG_NAME}",
    "token" = "${var.GITHUB_ACCESS_TOKEN}"
  })


}
