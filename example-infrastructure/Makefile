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

login: ## Run GCloud and Pulumi logins
	pulumi login
	gcloud auth login
	gcloud auth application-default login

init: ## See README, must provide "project"
	make login
	gcloud projects create $(project) --set-as-default
	pulumi stack init $(project)
	echo "----------------------------------------------------------------------------"
	echo "Follow the link to setup billing for the created GCloud account."
	echo "https://console.cloud.google.com/billing/linkedaccount?project=${project}"

build: ## Run pulumi up for infra setup
	pulumi up -p 5

reset: ## Run pulumi destroy and make build, must provide "project"
	pulumi destroy -p 5
	echo "----------------------------------------------------------------------------"
	echo "Sleeping for three minutes while resources clean up"
	sleep 180
	make build

destroy: ## Fully teardown Pulumi and GCloud, must provide "project"
	pulumi destroy -p 5
	pulumi stack rm ${project}
	gcloud projects delete ${project}

gen-key: ## Generate a service account JSON, must provide "project"
	mkdir ../.keys/ -p
	gcloud iam service-accounts create $(project)-$(USER)-dev \
    	--description="CDP Dev Service Account for $(USER)" \
    	--display-name="$(project)-$(USER)-dev"
	gcloud iam service-accounts add-iam-policy-binding \
		$(project)-$(USER)-dev@$(project).iam.gserviceaccount.com \
		--member=serviceAccount:$(project)-$(USER)-dev@$(project).iam.gserviceaccount.com \
		--role=roles/owner
	gcloud projects add-iam-policy-binding $(project) \
    	--member=serviceAccount:$(project)-$(USER)-dev@$(project).iam.gserviceaccount.com \
		--role=roles/owner
	gcloud iam service-accounts keys create ../.keys/$(project)-$(USER)-dev.json \
  		--iam-account \
		$(project)-$(USER)-dev@$(project).iam.gserviceaccount.com