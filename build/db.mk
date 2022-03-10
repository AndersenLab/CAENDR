include $(PROJECT_DIR)/build/help.mk

targets: clean venv clean-venv
.PHONY: targets

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
