PY ?= python

.PHONY: setup models run test eval bench smoke

setup models run test eval bench smoke:
	$(PY) tasks.py $@
