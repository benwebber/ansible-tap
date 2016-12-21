.PHONY: install \
        test \
        uninstall

ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

prefix    = $(HOME)/.ansible

all: test

install:
	install -D library/callback_plugins/tap.py $(prefix)/plugins/callback/tap.py

test:
	ANSIBLE_CALLBACK_PLUGINS=$(ROOT_DIR)/library/callback_plugins ANSIBLE_STDOUT_CALLBACK=tap py.test -v

uninstall:
	$(RM) $(prefix)/plugins/callback/tap.py
