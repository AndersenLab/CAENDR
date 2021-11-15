SHELL:=/bin/bash

MODULE_DIR = $(shell pwd)
PROJECT_DIR = $(MODULE_DIR)/..

include $(PROJECT_DIR)/make/module.mk
include $(MODULE_DIR)/module.env

all: help

# Add command to existing target 'pkg-dir' to delete the 
# shared package since it isn't required for this module
pkg-dir:: 
	@echo -e "\n$(COLOR_B)Removing shared package code...$(COLOR_N)"
	rm -rf $(MODULE_DIR)/caendr
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"


%:
	@:

