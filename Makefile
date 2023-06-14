.PHONY: help clean requirements build

.DEFAULT_GOAL := help

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@awk -F ':.*?## ' '/^[a-zA-Z]/ && NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

clean: ## remove stuff we don't need
	rm -fr docs/ docs0/

requirements: ## install Python requirements
	pip install -r requirements.txt

build: ## compile the Markdown docs
	python cyoa.py render index.md
