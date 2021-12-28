# printing these variables changes the font color until reverted back to N (ie "${COLOR_R} this text is red ${COLOR_N} this text is the default color ")
COLOR_R=\033[0;31m
COLOR_G=\033[0;32m
COLOR_Y=\033[1;33m
COLOR_B=\033[1;34m
COLOR_P=\033[0;35m
COLOR_C=\033[1;36m
COLOR_W=\033[1;37m
COLOR_A=\033[1;39m
COLOR_N=\033[0m

WHITESPACE_REGEX='/^\s*$$/d' 
COMMENT_REGEX='/^\#/d'
TF_VAR_PREFIX_REGEX='s/\(^.*\)/TF_VAR_\1/'

all: help
targets: help verify-env print-env confirm

.PHONY : targets
.DEFAULT : help

#~
help: #~
#~ Show this help.
	@echo -e "\nusage: make [target] ENV=[environment]\n"
	@fgrep -h "#~" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/\#~/   /' | sed -e 's/\(^[^#~].*\)/    \1/'
	@echo -e "\n\n\n"

verify-env:
ifeq ($(ENV),)
	@make help --no-print-directory
	@echo -e "$(COLOR_R)\nERROR: ENV must be defined!$(COLOR_N)\n\n"
	@false
endif

print-env: verify-env
	@echo -e "\n$(COLOR_P)****************************************************************************$(COLOR_N)"
	@echo -e "                    MODULE:       $(COLOR_C)GLOBAL$(COLOR_N)"
	@echo -e "                    ENVIRONMENT:  $(COLOR_Y)$(ENV)$(COLOR_N)"
	@echo -e "$(COLOR_P)****************************************************************************$(COLOR_N)\n"
	@cat $(GLOBAL_ENV_FILE)

confirm:
	@echo -e "\n$(COLOR_G)Press 'Enter' to continue or 'Ctrl + C' to cancel$(COLOR_N)\n" 
	@read CONFIRM
