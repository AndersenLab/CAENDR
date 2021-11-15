SHELL:=/bin/bash

MODULE_DIR = $(shell pwd)
PROJECT_DIR = $(MODULE_DIR)/../..

include $(PROJECT_DIR)/make/module.mk
include $(MODULE_DIR)/module.env

all: help

#~
run: #~
run: print-module-env install-pkg env-file venv
#~ Starts the Flask test server for local development and debugging
	@echo -e "\n$(COLOR_B)Starting flask debug server...$(COLOR_N)"
	@. $(MODULE_DIR)/venv/bin/activate && \
	$(LOAD_MODULE_ENV) && \
	export GOOGLE_APPLICATION_CREDENTIALS=$(TF_PATH)/terraform-service-account.json && \
	python main.py

%:
	@:
