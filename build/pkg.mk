include $(PROJECT_DIR)/build/help.mk

targets: clean venv
.PHONY: targets


#~
clean: #~
#~ Removes virtual environment, python cache, shared packages, and the 
#~ automatically generated .env file
clean:
	@echo -e "$(COLOR_B)Removing cached files...$(COLOR_N)"
	rm -rf $(PKG_DIR)/.pytest_cache
	rm -rf $(PKG_DIR)/venv
	find $(PKG_DIR) -name *.pyc -exec rm -rv {} +
	find $(PKG_DIR) -name __pycache__ -exec rm -rv {} +
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"


#~ 
venv: #~
#~ Creates a virtual python environment and installs packages from 'requirements.txt'
venv:
	@echo -e "\n$(COLOR_B)Installing python virtualenv and requirements.txt...$(COLOR_N)"
	virtualenv --python=python3 $(PKG_DIR)/venv; \
	$(PKG_DIR)/venv/bin/python -m pip install --upgrade pip; \
	$(PKG_DIR)/venv/bin/pip install -r $(PKG_DIR)/requirements.txt
	@echo -e "$(COLOR_G)DONE!$(COLOR_N)\n"
