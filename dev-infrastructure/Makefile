.PHONY: help login init build clean reset destroy gen-key
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

login: ## Run GCloud and Pulumi logins
	pulumi logout
	pulumi login
	gcloud auth login
	gcloud auth application-default login

init: ## See README, must provide "project"
	gcloud projects create $(project) --set-as-default
	pulumi stack init $(project)
	echo "----------------------------------------------------------------------------"
	echo "Follow the link to setup billing for the created GCloud account."
	echo "https://console.cloud.google.com/billing/linkedaccount?project=${project}"

build: ## Run pulumi up for infra setup
	pulumi up -p 4

clean: ## Remove all database documents and filestore objects, must provide "key"
	clean_cdp_database ${key}
	clean_cdp_filestore ${key}

reset: ## Run pulumi destroy and make build, must provide "project"
	pulumi destroy -p 4
	echo "----------------------------------------------------------------------------"
	echo "Sleeping for three minutes while resources clean up"
	sleep 180
	make build

destroy: ## Fully teardown Pulumi and GCloud, must provide "project"
	pulumi stack rm ${project} --force
	gcloud projects delete ${project}

gen-key: ## Generate a service account JSON, must provide "project"
	mkdir ../.keys/ -p
	gcloud iam service-accounts create $(project) \
    	--description="CDP Dev Service Account for $(USER)" \
    	--display-name="$(project)"
	gcloud projects add-iam-policy-binding $(project) \
    	--member="serviceAccount:$(project)@$(project).iam.gserviceaccount.com" \
		--role="roles/owner"
	gcloud iam service-accounts keys create ../.keys/$(project).json \
  		--iam-account "$(project)@$(project).iam.gserviceaccount.com"
	echo "----------------------------------------------------------------------------"
	echo "Sleeping for one minute while resources set up"
	sleep 60
	echo "Key generation complete"
