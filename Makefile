SHELL:=/bin/bash
PROJECT_DIR = $(shell pwd)

include $(PROJECT_DIR)/build/help.mk

MODULE_NAME = "GLOBAL"

ENV_PATH = $(PROJECT_DIR)/env/$(ENV)
GLOBAL_ENV_FILE = $(ENV_PATH)/global.env
SECRET_ENV_FILE = $(ENV_PATH)/secret.env
TF_PATH = $(PROJECT_DIR)/tf
MODULE_PATH = $(PROJECT_DIR)/src/modules

-include $(GLOBAL_ENV_FILE)

LOAD_GLOBAL_ENV=export $$(cat $(GLOBAL_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | xargs)
LOAD_TF_VAR=export $$(cat $(GLOBAL_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | sed $(TF_VAR_PREFIX_REGEX) | xargs)
LOAD_SECRET_TF_VAR=export $$(cat $(SECRET_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | sed $(TF_VAR_PREFIX_REGEX) | xargs)

all: help
targets: clean-all dev build-all-containers publish-all-containers configure-all cloud-resource-plan cloud-resource-deploy cloud-resource-destroy

.PHONY : targets
.DEFAULT : help

#~
clean-all: #~
clean-all: clean
#~ Runs 'make clean' for all services, deletes cached python files 
#~ and removes any previously generated terraform plan
	@echo -e "\n$(COLOR_B)Cleaning module directories...$(COLOR_N)"
#	@$(MAKE) -C $(MODULE_PATH)/api/pipeline-task print-module-env clean --no-print-directory
#	@$(MAKE) -C $(MODULE_PATH)/db-ops print-module-env clean --no-print-directory
#	@$(MAKE) -C $(MODULE_PATH)/img_thumb_gen print-module-env clean --no-print-directory
#	@$(MAKE) -C $(MODULE_PATH)/site print-module-env clean --no-print-directory
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

#~
build-all-containers: #~
#~ Runs 'make build-container ENV=[environment]' for all services 
#~ and tags them with the container name and version from the global.env file
	@echo -e "\n$(COLOR_B)Building module container images...$(COLOR_N)"
#	@$(MAKE) -C $(MODULE_PATH)/api/pipeline-task build-container ENV=$(ENV) --no-print-directory
#	@$(MAKE) -C $(MODULE_PATH)/db-ops build-container ENV=$(ENV) --no-print-directory
#	@$(MAKE) -C $(MODULE_PATH)/site build-container ENV=$(ENV) --no-print-directory
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

#~
publish-all-containers: #~
#~ Runs 'make publish-container ENV=[environment]' for all services 
#~ and tags them with the container name and version from the global.env file
	@echo -e "\n$(COLOR_B)Publishing module container images...$(COLOR_N)"
#	$(MAKE) -C $(MODULE_PATH)/api/pipeline-task publish-container ENV=$(ENV) --no-print-directory
#	$(MAKE) -C $(MODULE_PATH)/db-ops publish-container ENV=$(ENV) --no-print-directory
#	$(MAKE) -C $(MODULE_PATH)/site publish-container ENV=$(ENV) --no-print-directory
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

#~
configure-all: #~
#~ Runs 'make configure ENV=[environment]' for all services
configure-all: verify-env print-env confirm
	@echo -e "\n$(COLOR_B)Configuring all modules...$(COLOR_N)"
#	@$(MAKE) -C $(MODULE_PATH)/api/pipeline-task configure-auto ENV=$(ENV) --no-print-directory
#	@$(MAKE) -C $(MODULE_PATH)/db-ops configure-auto ENV=$(ENV) --no-print-directory
#	@$(MAKE) -C $(MODULE_PATH)/img-thumb-gen configure-auto ENV=$(ENV) --no-print-directory
#	@$(MAKE) -C $(MODULE_PATH)/site configure-auto ENV=$(ENV) --no-print-directory
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"
	

#~
cloud-resource-plan: #~
#~ Generates a terraform plan for the infrastructure described in ./env/[environment]/terraform  
#~ including any service-specific terraform modules that are required
cloud-resource-plan: configure-all
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && \
	cd $(TF_PATH) && terraform init && terraform plan -out tf-plan
	@echo -e "\n\nRun this command to apply the terraform plan: $(COLOR_G)'make cloud-resource-deploy ENV=$(ENV)'$(COLOR_N)\n" 

#~
cloud-resource-deploy: #~
#~ Executes the generated terraform plan for deploying infrastructure described 
#~ in ./env/[environment]/terraform including any service-specific terraform modules that are required
cloud-resource-deploy: configure-all
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && \
	cd $(TF_PATH) && terraform init && terraform plan -out tf-plan && \
	cd $(PROJECT_DIR) && $(MAKE) -C . confirm --no-print-directory && \
	cd $(TF_PATH) && terraform apply "tf-plan"

#~
cloud-resource-destroy: #~
#~ Destroys all cloud resources provisioned by terraform
cloud-resource-destroy: configure-all
	@gcloud config set project ${GOOGLE_CLOUD_PROJECT_ID} && \
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && \
	cd $(PROJECT_DIR) && $(MAKE) -C . confirm --no-print-directory && \
	cd $(TF_PATH) && terraform init && terraform destroy

%:
	@:
