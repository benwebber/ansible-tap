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


def clean_tags(tags):
    return [tag.lower() for tag in tags]


def is_todo(task):
    return Tag.TODO.value in clean_tags(task.tags)


def is_diagnostic(task):
    return Tag.DIAGNOSTIC.value in clean_tags(task.tags)


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

    @classmethod
    def ok(cls, result):
        """
        Render a passed test.
        """
        directive = '# TODO' if is_todo(result._task) else None
        description = cls._describe(result)
        return cls._tap(cls.OK, description, directive=directive)

    @classmethod
    def skip(cls, result):
        """
        Render a skipped test.
        """
        description = cls._describe(result)
        directive = '# SKIP {}'.format(result._result['skip_reason'])
        return cls._tap(cls.OK, description, directive=directive)

    @classmethod
    def not_ok(cls, result):
        """
        Render a failed test.
        """
        directive = '# TODO' if is_todo(result._task) else None
        description = cls._describe(result)
        return cls._tap(cls.NOT_OK, description, directive=directive)

    @staticmethod
    def _describe(result):
        """
        Construct a test line description based on the name of the Ansible
        module and task name.
        """
        description = '{}'.format(result._task.action)
        if result._task.name:
            description = '{}: {}'.format(description, result._task.name)
        return description

    @staticmethod
    def _tap(status, description, directive=None):
        """
        Render a TAP test line.
        """
        test_line = '{} - {}'.format(status, description)
        if directive:
            test_line += ' {}'.format(directive)
        lines = [test_line]
        return '\n'.join(lines)

    def v2_playbook_on_start(self, playbook):
        self._display.display('TAP version 13')

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._display.display(self.not_ok(result))
        # Print reason for failure if this was not an expected failure.
        status = TestResult.EXPECTED if is_todo(result._task) else TestResult.FAILED
        if status == TestResult.FAILED:
            self._display.display(indent(dump_yaml(result._result)))
        self.counter.update(status.value)

    def v2_runner_on_ok(self, result):
        if is_diagnostic(result._task):
            self._display.display('# {}'.format(self._describe(result)))
            return
        status = TestResult.UNEXPECTED if is_todo(result._task) else TestResult.PASSED
        self.counter.update(status.value)
        self._display.display(self.ok(result))

    def v2_runner_on_skipped(self, result):
        self._display.display(self.skip(result))
        self.counter.update(TestResult.SKIPPED.value)

    def v2_playbook_on_stats(self, stats):
        self._display.display('1..{}'.format(sum(self.counter.values())))
        # Because tests set `ignore_errors`, we need to call exit() ourselves.
        if self.counter['failed']:
            sys.exit(TaskQueueManager.RUN_FAILED_HOSTS)
