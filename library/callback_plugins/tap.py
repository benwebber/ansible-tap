#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
)

import collections
import sys

from enum import Enum
import yaml

from ansible import constants as C
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.plugins.callback import CallbackBase
from ansible.utils.color import stringc

__metaclass__ = type


def indent(text, indent=2, char=' '):
    return '\n'.join('{indent}{line}'.format(indent=indent*char, line=line)
                     for line in text.splitlines())


def dump_yaml(data, **kwargs):
    return yaml.dump(data, Dumper=AnsibleDumper, allow_unicode=True,
                     default_flow_style=False, explicit_start=True,
                     explicit_end=True, **kwargs).strip()


class TestResult(Enum):
    PASSED = ('passed',)
    FAILED = ('failed',)
    EXPECTED = ('expected',)
    UNEXPECTED = ('unexpected',)
    SKIPPED = ('skipped',)


class Tag(Enum):
    TODO = 'todo'
    DIAGNOSTIC = 'diagnostic'


class CallbackModule(CallbackBase):
    """
    TAP output for Ansible.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'tap'

    if sys.stdout.isatty():
        OK = stringc('ok', C.COLOR_OK)
        NOT_OK = stringc('not ok', C.COLOR_ERROR)
    else:
        OK = 'ok'
        NOT_OK = 'not ok'

    def __init__(self):
        super(CallbackModule, self).__init__()
        # Play stats will include all tasks. We want to exclude setup/teardown
        # tasks (tagged with 'diagnostic') from the final test count.
        self.counter = collections.Counter()

    def description(self, result):
        """
        Construct a test line description based on the name of the Ansible
        module and task name.
        """
        description = '{0}'.format(result._task.action)
        if result._task.name:
            description = '{0}: {1}'.format(description, result._task.name)
        return description

    def ok(self, result):
        """
        Print a passed test.
        """
        cleaned_tags = self._clean_tags(result._task.tags)
        if Tag.TODO.value in cleaned_tags:
            directive = '# TODO'
        else:
            directive = None
        description = self.description(result)
        output = self._tap(self.OK, description, directive=directive)
        self._display.display(output)

    def skip(self, result):
        """
        Print a skipped test.
        """
        description = self.description(result)
        directive = '# SKIP {0}'.format(result._result['skip_reason'])
        output = self._tap(self.OK, description, directive=directive)
        self._display.display(output)

    def not_ok(self, result):
        """
        Print a failed test.
        """
        cleaned_tags = self._clean_tags(result._task.tags)
        if Tag.TODO.value in cleaned_tags:
            directive = '# TODO'
        else:
            directive = None
        description = self.description(result)
        output = self._tap(self.NOT_OK, description, directive=directive)
        self._display.display(output)

    def _tap(self, status, description, directive=None):
        """
        Print a TAP test line.
        """
        test_line = '{0} - {1}'.format(status, description)
        if directive:
            test_line += ' {0}'.format(directive)
        lines = [test_line]
        return '\n'.join(lines)

    @staticmethod
    def _clean_tags(tags):
        return [tag.lower() for tag in tags]

    def v2_playbook_on_start(self, playbook):
        self._display.display('TAP version 13')

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.not_ok(result)
        cleaned_tags = self._clean_tags(result._task.tags)
        # Print reason for failure if this was not an expected failure.
        if Tag.TODO.value not in cleaned_tags:
            self._display.display(indent(dump_yaml(result._result)))
            self.counter.update(TestResult.EXPECTED.value)
            return
        self.counter.update(TestResult.FAILED.value)

    def v2_runner_on_ok(self, result):
        cleaned_tags = self._clean_tags(result._task.tags)
        if Tag.DIAGNOSTIC.value in cleaned_tags:
            self._display.display('# {0}'.format(self.description(result)))
            return
        if Tag.TODO.value in cleaned_tags:
            self.counter.update(TestResult.UNEXPECTED.value)
        else:
            self.counter.update(TestResult.PASSED.value)
        self.ok(result)

    def v2_runner_on_skipped(self, result):
        self.skip(result)
        self.counter.update(TestResult.SKIPPED.value)

    def v2_playbook_on_stats(self, stats):
        self._display.display('1..{}'.format(sum(self.counter.values())))
        # Because tests set `ignore_errors`, we need to call exit() ourselves.
        if self.counter['failed']:
            sys.exit(TaskQueueManager.RUN_FAILED_HOSTS)
