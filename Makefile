PYTHON ?= python3

.PHONY: setup validate test

setup:
	$(PYTHON) -m pip install -r requirements-dev.txt

validate:
	$(PYTHON) scripts/validate_repo.py .

test:
	$(PYTHON) -m unittest discover -s tests -v
