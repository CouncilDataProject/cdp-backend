.PHONY: clean build gen-docs docs help
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

init:  ## See README, must provide "project_name"
	pulumi login
	gcloud auth login
	gcloud auth application-default login
	gcloud projects create $(project_name) --set-as-default
	pulumi stack init $(project_name)
	mkdir ../.keys/ -p
	gcloud iam service-accounts create $(project_name)-$(USER)-dev \
    	--description="CDP Dev Service Account for $(USER)" \
    	--display-name="$(project_name)-$(USER)-dev"
	gcloud iam service-accounts keys create ../.keys/$(project_name)-$(USER)-dev.json \
  		--iam-account \
		$(project_name)-$(USER)-dev@$(project_name).iam.gserviceaccount.com
	gcloud iam service-accounts add-iam-policy-binding \
		$(project_name)-$(USER)-dev \
		--member="serviceAccount:$(project_name)-$(USER)-dev@$(project_name).iam.gserviceaccount.com" \
		--role="roles/owner"

gen-key:  ## Generate a service account JSON, must provide "project_name"
	gcloud iam service-accounts create $(project_name)-$(USER)-dev \
    	--description="CDP Dev Service Account for $(USER)" \
    	--display-name="$(project_name)-$(USER)-dev"
	gcloud iam service-accounts add-iam-policy-binding \
		$(project_name)-$(USER)-dev@$(project_name).iam.gserviceaccount.com \
		--member=serviceAccount:$(project_name)-$(USER)-dev@$(project_name).iam.gserviceaccount.com \
		--role=roles/owner
	gcloud projects add-iam-policy-binding $(project_name) \
    	--member=serviceAccount:$(project_name)-$(USER)-dev@$(project_name).iam.gserviceaccount.com \
		--role=roles/owner
	gcloud iam service-accounts keys create ../.keys/$(project_name)-$(USER)-dev.json \
  		--iam-account \
		$(project_name)-$(USER)-dev@$(project_name).iam.gserviceaccount.com

build:  ## run pulumi up for infra setup
	pulumi up -p 5