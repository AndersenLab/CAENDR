SHELL:=/bin/bash
PROJECT_DIR = $(shell pwd)

include $(PROJECT_DIR)/build/admin.mk
include $(PROJECT_DIR)/build/help.mk

MODULE_NAME = "GLOBAL"

ENV_PATH = $(PROJECT_DIR)/env/$(ENV)
GLOBAL_ENV_FILE = $(ENV_PATH)/global.env
SECRET_ENV_FILE = $(ENV_PATH)/secret.env
TF_PATH = $(PROJECT_DIR)/tf/caendr

MODULE_PATH = $(PROJECT_DIR)/src/modules

-include $(GLOBAL_ENV_FILE)

LOAD_GLOBAL_ENV=export $$(cat $(GLOBAL_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | xargs)
LOAD_GLOBAL_ENV=export $$(cat $(GLOBAL_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | xargs)
LOAD_TF_VAR=export $$(cat $(GLOBAL_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | sed $(TF_VAR_PREFIX_REGEX) | xargs)
LOAD_SECRET=export $$(cat $(SECRET_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | xargs)
LOAD_SECRET_TF_VAR=export $$(cat $(SECRET_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | sed $(TF_VAR_PREFIX_REGEX) | xargs)

TF_SELECT_WORKSPACE=(terraform workspace new $(ENV) || (echo "Switching to existing workspace \"$(ENV)\"" && terraform workspace select $(ENV)))

all: help
targets: configure cloud-resource-plan cloud-resource-deploy cloud-resource-destroy 

.PHONY : targets
.DEFAULT : help

#~
configure: #~
#~ If using Ubuntu for the development environment, use this target to install
#~ required system packages for testing and deploying project modules
#~ including docker, google cloud sdk, terraform, etc...
configure:
ifeq ($(getend group admin),)
else
	@echo -e "\n$(COLOR_B)Creating docker user group...$(COLOR_N)" && \
	sudo groupadd docker
endif

	@echo -e "\n$(COLOR_B)Installing system packages...$(COLOR_N)"
	sudo apt-get update && sudo apt-get install \
		apt-transport-https \
		build-essential \
		ca-certificates \
		curl \
		fuse \
		gawk \
		git \
		gnupg \
		graphviz \
		gunicorn \
		gzip \
		libbz2-dev \
		libgraphviz-dev \
		liblzma-dev \
		libncursesw5-dev \
		libncurses5-dev \
		libxml2 \
		libxml2-dev \
		libxmlsec1-dev \
		libxmlsec1-openssl \
		make \
		pkg-config \
		python3 \
		python3-dev \
		python3-venv \
		python3-virtualenv \
		software-properties-common \
		tabix \
		virtualenv \
		vim \
		wget \
		xmlsec1 \
		zip \
		zlib1g-dev

	@echo -e "\n$(COLOR_B)Installing docker.io...$(COLOR_N)"
	sudo apt-get install docker.io

	@echo -e "\n$(COLOR_B)Adding current USER:$(USER) to docker group...$(COLOR_N)"
	sudo usermod -aG docker $(USER)

	@echo -e "\n$(COLOR_B)Installing Terraform...$(COLOR_N)" && \
	curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add - && \
	sudo apt-add-repository "deb [arch=$$(dpkg --print-architecture) ] https://apt.releases.hashicorp.com $$(lsb_release -cs) main" && \
	sudo apt-get update && sudo apt-get install terraform

	@echo -e "\n$(COLOR_B)Installing Google Cloud SDK...$(COLOR_N)" && \
	echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
	curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
	sudo apt-get update && sudo apt-get install google-cloud-sdk

	@echo -e "\n$(COLOR_B)Installing Google Cloud SQL Proxy...$(COLOR_N)" && \
	wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy && \
	chmod +x cloud_sql_proxy && \
	mkdir /cloudql

	@echo -e "\n$(COLOR_B)Configuring Google Cloud SDK...$(COLOR_N)" && \
	gcloud init && \
	gcloud auth login && \
	gcloud auth application-default login && \
	gcloud auth configure-docker


#~
cloud-resource-init: #~
#~ Initializes terraform providers and loads the backend.hcl config 
#~ if it exists in the environment directory, or use a local backend otherwise.
cloud-resource-init:
	@echo -e "\n$(COLOR_B)Initializing Terraform...$(COLOR_N)"
ifneq ("$(wildcard $(ENV_PATH)/backend.hcl)","")
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && cd $(TF_PATH) && \
	export DEBUG=0 && \
	terraform init -backend-config=$(ENV_PATH)/backend.hcl
else
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && cd $(TF_PATH) && \
	export DEBUG=0 && \
	terraform init
endif


#~
cloud-resource-plan: #~
#~ Generates a terraform plan for the infrastructure described in ./env/[environment]/terraform  
#~ including any service-specific terraform modules that are required
cloud-resource-plan: cloud-resource-init
	@echo -e "\n$(COLOR_B)Creating Terraform plan for changes to cloud infrastructure...$(COLOR_N)" && \
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && \
	cd $(TF_PATH) && rm -rf tf_plan && \
	$(TF_SELECT_WORKSPACE) && \
	export DEBUG=0 && \
	terraform plan -out tf_plan
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"
	@echo -e "\n\nRun this command to apply the terraform plan: $(COLOR_G)'make cloud-resource-deploy ENV=$(ENV)'$(COLOR_N)\n" 


#~
cloud-resource-deploy: #~
#~ Executes the generated terraform plan for deploying infrastructure described 
#~ in ./env/[environment]/terraform including any service-specific terraform modules that are required
cloud-resource-deploy: cloud-resource-init
	@echo -e "\n$(COLOR_B)Deploying the Terraform cloud resource plan...$(COLOR_N)" && \
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && \
	cd $(TF_PATH) && \
	rm -rf tf_plan && \
	$(TF_SELECT_WORKSPACE) && \
	export DEBUG=0 && \
	terraform plan -out tf_plan && \
	$(MAKE) -C $(PROJECT_DIR) confirm --no-print-directory && \
	export DEBUG=0 && \
	terraform apply "tf_plan" 
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"


#~
terragrunt-shell: #~
#~ Deploys the site
terragrunt-shell: 
	@echo -e "\n$(COLOR_B)Initializing Terraform...$(COLOR_N)"
ifneq ("$(wildcard $(ENV_PATH)/backend.hcl)","")
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET) && cd $(TF_PATH) && \
	bash 
else
	$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && cd $(TF_PATH) && \
	bash
endif

#~
cloud-resource-destroy: #~
#~ Destroys all cloud resources provisioned by terraform
cloud-resource-destroy: cloud-resource-init
	@echo -e "\n$(COLOR_B)DESTROYING ALL TERRAFORM PROVISIONED CLOUD RESOURCES.\nARE YOU SURE YOU WANT TO DO THIS?$(COLOR_N)"
	@$(LOAD_GLOBAL_ENV) && $(LOAD_TF_VAR) && $(LOAD_SECRET_TF_VAR) && \
	$(MAKE) -C $(PROJECT_DIR) confirm --no-print-directory && \
	cd $(TF_PATH) && rm -rf tf_plan && \
	$(TF_SELECT_WORKSPACE) && \
	terraform destroy
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"



%:
	@:
