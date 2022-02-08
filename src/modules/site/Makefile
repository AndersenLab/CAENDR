SHELL:=/bin/bash

MODULE_DIR = $(shell pwd)
PROJECT_DIR = $(MODULE_DIR)/../../..

include $(MODULE_DIR)/module.env
include $(PROJECT_DIR)/build/module.mk

all: help


#~
create-schema: #~
#~ Creates the SQL schema
create-schema: print-module-env dot-env venv install-pkg
	@echo -e "\n$(COLOR_B)Creating DB schema...$(COLOR_N)"
	@. $(MODULE_DIR)/venv/bin/activate && \
	$(LOAD_MODULE_ENV) && \
	python create_schema.py

#~
postgres-start: #~
#~ Starts the local postgres container
postgres-start: print-module-env dot-env venv install-pkg
	@echo -e "\n$(COLOR_B)Staring local postgres container...$(COLOR_N)"
	$(LOAD_MODULE_ENV) && \
	docker-compose up -d postgres

#~
postgres-stop: #~
#~ Stops the local postgres container
postgres-stop: 
	@echo -e "\n$(COLOR_B)Stopping local postgres container...$(COLOR_N)"
	$(LOAD_MODULE_ENV) && \
	docker-compose down postgres

#~
cloud-sql-proxy-start: #~
#~ Starts the cloud-sql-proxy container
cloud-sql-proxy-start: print-module-env dot-env venv install-pkg
	@echo -e "\n$(COLOR_B)Starting cloud-sql-proxy container...$(COLOR_N)"
	$(LOAD_MODULE_ENV) && \
	docker-compose create cloud-sql-proxy && \
	docker-compose start cloud-sql-proxy

#~
cloud-sql-proxy-stop: #~
#~ Stops the cloud-sql-proxy container
cloud-sql-proxy-stop: 
	@echo -e "\n$(COLOR_B)Stopping cloud-sql-proxy container...$(COLOR_N)"
	$(LOAD_MODULE_ENV) && \
	docker-compose down cloud-sql-proxy

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

