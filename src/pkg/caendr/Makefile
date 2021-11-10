SHELL:=/bin/bash

PKG_DIR = $(shell pwd)
PROJECT_DIR = $(PKG_DIR)/../../..

include $(PROJECT_DIR)/build/pkg.mk

targets: run
.PHONY: targets

all: help

#~
test: #~
test: FORCE
#~ Runs all tests from the test directory
	@. $(PKG_DIR)/venv/bin/activate && \
	pytest -vv --print


%:
	@:


