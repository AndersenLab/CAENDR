SHELL:=/bin/bash

MODULE_DIR = $(shell pwd)
PROJECT_DIR = $(MODULE_DIR)/../../..

include $(MODULE_DIR)/module.env
include $(PROJECT_DIR)/build/module.mk

all: help

#~
run: #~
#~ Runs the indel primer locally
# TODO: load conda environment
run: print-module-env dot-env venv install-pkg
	@echo -e "\n$(COLOR_B)Starting Indel Primer...$(COLOR_N)"
	@. $(MODULE_DIR)/venv/bin/activate && \
	$(LOAD_MODULE_ENV) && \
	python main.py


%:
	@:

