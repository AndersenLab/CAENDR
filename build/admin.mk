ADMIN_ENV_PATH = $(PROJECT_DIR)/env/admin
ADMIN_ENV_FILE = $(PROJECT_DIR)/env/admin/global.env
ADMIN_TF_PATH = $(PROJECT_DIR)/tf/admin

include $(ENV_FILE)

LOAD_ADMIN_ENV=export $$(cat $(ADMIN_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | xargs)
LOAD_ADMIN_TF_VAR=export $$(cat $(ADMIN_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | sed $(TF_VAR_PREFIX_REGEX) | xargs)
LOAD_ADMIN_SECRET_TF_VAR=export $$(cat $(ADMIN_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | sed $(TF_VAR_PREFIX_REGEX) | xargs)

all: help
targets: cloud-resource-init

.PHONY: targets

#~
admin-cloud-resource-init: #~
#~ Sets up the Administrative Google Cloud Project and configures
#~ a Cloud Storage bucket to track the tfstate for all environments
admin-cloud-resource-init:
	@echo -e "\n$(COLOR_B)Initializing cloud resources required for Terraform...$(COLOR_N)"
	@$(LOAD_ADMIN_ENV) && $(LOAD_ADMIN_TF_VAR) && $(LOAD_ADMIN_SECRET_TF_VAR) && \
	cd $(ADMIN_TF_PATH) && rm -rf tf_plan && \
	terraform init && \
	(terraform workspace new admin || terraform workspace select admin) && \
	terraform plan -out tf_plan && \
	cd $(PROJECT_DIR) && $(MAKE) -C . confirm --no-print-directory && \
	cd $(ADMIN_TF_PATH) && terraform apply tf_plan
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"
