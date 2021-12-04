SHELL:=/bin/bash

MODULE_DIR = $(shell pwd)
PROJECT_DIR = $(MODULE_DIR)/../../../..

include $(MODULE_DIR)/module.env
include $(PROJECT_DIR)/build/module.mk

all: help


#~
run: #~
run: print-module-env dot-env venv install-pkg
#~ Starts the Flask test server for local development and debugging
	@echo -e "\n$(COLOR_B)Starting flask debug server...$(COLOR_N)"
	@. $(MODULE_DIR)/venv/bin/activate && \
	$(LOAD_MODULE_ENV) && \
	python main.py

%:
	@:
