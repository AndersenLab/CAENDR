# Required definitions:
# MODULE_NAME, MODULE_DIR, PROJECT_DIR

include $(PROJECT_DIR)/build/help.mk

ENV_PATH = $(PROJECT_DIR)/env/$(ENV)
ENV_FILE = $(ENV_PATH)/global.env
TF_PATH = $(PROJECT_DIR)/tf/caendr

MODULE_ENV_FILE = $(MODULE_DIR)/module.env
MODULE_ENV_FILE_GENERATED = $(MODULE_DIR)/.env
MODULE_PKG_DIR = $(MODULE_DIR)/caendr
PKG_SETUP_DIR = $(PROJECT_DIR)/src/pkg/caendr


-include $(ENV_FILE)
include $(MODULE_ENV_FILE)

LOAD_MODULE_ENV=export $$(cat $(MODULE_ENV_FILE_GENERATED) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX) | xargs)

targets: clean install-pkg dot-env configure venv clean-venv container publish-container print-module-env print-ver
.PHONY: targets

#~
clean: #~
#~ Removes the python cache and generated .env file
clean:
	@echo -e "$(COLOR_B)Removing cached files...$(COLOR_N)"
	rm -f $(MODULE_ENV_FILE_GENERATED)
	rm -rf $(MODULE_DIR)/.download
	rm -rf $(MODULE_PKG_DIR)
	find $(MODULE_DIR) -name *.pyc -exec rm -rv {} +
	find $(MODULE_DIR) -name __pycache__ -exec rm -rv {} +
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

#~
install-pkg: #~
#~ Uses pip to install the local CAENDR package in the module's virtualenv
install-pkg:
	@echo -e "\n$(COLOR_B)Installing CAENDR package...$(COLOR_N)" && \
	. $(MODULE_DIR)/venv/bin/activate && \
	python -m pip install -e $(PKG_SETUP_DIR) && \
	echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

#~
dot-env: #~
dot-env: verify-env
#~ Merges the definitions from the environment global.env config and the 
#~ module.env to create the .env file to be deployed inside the container
	@echo -e "\n$(COLOR_B)Writing new .env file...$(COLOR_N)"
	rm -f $(MODULE_ENV_FILE_GENERATED) 
	@echo -e "# DO NOT EDIT THIS FILE! - IT IS AUTOMATICALLY GENERATED \n" >> $(MODULE_ENV_FILE_GENERATED) ;\
	(cat $(ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX)) >> $(MODULE_ENV_FILE_GENERATED) ;\
	(cat $(MODULE_ENV_FILE) | sed $(WHITESPACE_REGEX) | sed $(COMMENT_REGEX)) >> $(MODULE_ENV_FILE_GENERATED)
	@ls $(MODULE_ENV_FILE_GENERATED)
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

#~
configure: #~
#~ Removes all cached files (including venv), generates the module's .env file,
#~ and copies the code for the shared/caendr package into the module directory
configure: print-module-env confirm clean clean-venv dot-env install-pkg

#~ 
venv: #~
#~ Creates a virtual python environment and installs the packages 
#~ from 'requirements.txt' and the caendr local package from source
venv:
	@echo -e "\n$(COLOR_B)Installing python virtualenv and requirements.txt...$(COLOR_N)"
	virtualenv --python=python3 $(MODULE_DIR)/venv && \
	$(MODULE_DIR)/venv/bin/python -m pip install --upgrade pip && \
	$(MODULE_DIR)/venv/bin/python -m pip install -r $(MODULE_DIR)/requirements.txt
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"
	$(MAKE) install-pkg


#~
clean-venv: #~
#~ Removes the virtual environment
clean-venv:
	@echo -e "$(COLOR_B)Removing virtual environment...$(COLOR_N)"
	rm -rf $(MODULE_DIR)/venv
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"


#~
container: #~
#~ Removes the virtual environment and python cache, regenerates the module .env file, 
#~ copies the code for the shared/caendr package into the module directory, and
#~ builds the container for the module and tags it with the name and version from module.env
container: verify-env print-module-env print-ver confirm clean clean-venv dot-env
	@echo -e "\n$(COLOR_B)Copying caendr package source locally...$(COLOR_N)"
	$(MAKE) -C $(PKG_SETUP_DIR) clean --no-print-directory && \
	cp -r $(PKG_SETUP_DIR) $(MODULE_DIR) && \
	echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"
	
	@echo -e "\n$(COLOR_B)Building container image...$(COLOR_N)" && \
	docker build $(MODULE_DIR) -t gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${MODULE_NAME}:${MODULE_VERSION} && \
	echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

	@echo -e "\n$(COLOR_B)Removing local caendr package source copy$(COLOR_N)" && \
	$(MAKE) -C $(MODULE_DIR) clean --no-print-directory && \
	echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

#~
publish-container: #~
#~ Configures and builds the container for the module and tags it with the 
#~ name and version from module.env before uploading it to the google container registry
publish-container: build-container
	@echo -e "\n$(COLOR_B)Publishing container image to gcr...$(COLOR_N)"
	docker push gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${MODULE_NAME}:${MODULE_VERSION}
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

build-container-auto:configure-auto
	@echo -e "\n$(COLOR_B)Building container image...$(COLOR_N)"
	docker build $(MODULE_DIR) -t gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${MODULE_NAME}:${MODULE_VERSION}
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

publish-container-auto: build-container-auto
	@echo -e "\n$(COLOR_B)Publishing container image to gcr...$(COLOR_N)"
	docker push gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${MODULE_NAME}:${MODULE_VERSION}
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"

print-module-env: verify-env
	@echo -e "\n$(COLOR_P)****************************************************************************$(COLOR_N)"
	@echo -e "                    MODULE:       $(COLOR_C)$(MODULE_NAME)$(COLOR_N)"
	@echo -e "                    ENVIRONMENT:  $(COLOR_Y)$(ENV)$(COLOR_N)"
	@echo -e "$(COLOR_P)****************************************************************************$(COLOR_N)"

print-ver:
	@echo -e "$(COLOR_P)****************************************************************************$(COLOR_N)"
	@echo -e " CONTAINER: $(COLOR_W)gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${MODULE_NAME}:${MODULE_VERSION}$(COLOR_N)"
	@echo -e "$(COLOR_P)****************************************************************************$(COLOR_N)"
