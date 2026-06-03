SHELL:=/bin/bash

MODULE_DIR = $(shell pwd)
PROJECT_DIR = $(MODULE_DIR)/../../..

include $(MODULE_DIR)/module.env
include $(PROJECT_DIR)/build/db.mk
include $(PROJECT_DIR)/build/module.mk

all: help


#~
run: #~
#~ Starts the Flask test server for local development and debugging
run: print-module-env dot-env venv install-pkg
	@echo -e "\n$(COLOR_B)Starting flask debug server...$(COLOR_N)"
	@. $(MODULE_DIR)/venv/bin/activate && \
	$(LOAD_MODULE_ENV) && \
	FLASK_RUN_PORT=8080 flask run --host=0.0.0.0 --cert=adhoc


%:
	@:

