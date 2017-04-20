# -*- coding: utf-8 -*-

import os.path

import pytest
import tap.line
import tap.parser


pytest_plugins = ['pytester']


@pytest.fixture
def run_playbook(testdir):
    def _run_playbook(playbook):
        playbook = os.path.join(os.path.dirname(__file__), 'playbooks', playbook)
        command = ['ansible-playbook', '-i', 'localhost,', '-c', 'local', playbook]
        return testdir.run(*command)
    return _run_playbook


@pytest.fixture
def parser():
    return tap.parser.Parser()


class TestTAPStream(object):
    def test_tap_version(self, run_playbook, parser):
        result = run_playbook('test_tap_version.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        version = lines[0]
        assert version.category == 'version'
        assert version.version == 13

    def test_expected_success(self, run_playbook, parser):
        result = run_playbook('test_expected_success.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        test = lines[1]
        assert result.ret == 0
        assert test.category == 'test'
        assert test.ok is True
        assert test.description == '- assert: expect success'
        assert test.skip is False
        assert test.todo is False

    def test_unexpected_success(self, run_playbook, parser):
        result = run_playbook('test_unexpected_success.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        test = lines[1]
        assert result.ret == 0
        assert test.category == 'test'
        assert test.ok is True
        assert test.description == '- assert: expect failure'
        assert test.skip is False
        assert test.todo is True

    def test_expected_failure(self, run_playbook, parser):
        result = run_playbook('test_expected_failure.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        test = lines[1]
        assert result.ret == 0
        assert test.category == 'test'
        assert test.ok is False
        assert test.description == '- assert: expect failure'
        assert test.skip is False
        assert test.todo is True

    def test_unexpected_failure(self, run_playbook, parser):
        result = run_playbook('test_unexpected_failure.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        test = lines[1]
        assert result.ret == 2
        assert test.category == 'test'
        assert test.ok is False
        assert test.description == '- assert: expect success'
        assert test.skip is False
        assert test.todo is False

    def test_skip(self, run_playbook, parser):
        result = run_playbook('test_skip.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        test = lines[1]
        assert result.ret == 0
        assert test.category == 'test'
        assert test.ok is True
        assert test.directive.reason == 'Conditional check failed'
        assert test.skip is True
        assert test.todo is False

    def test_skip_with_items(self, run_playbook, parser):
        result = run_playbook('test_skip_with_items.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        test = lines[1]
        assert result.ret == 0
        assert test.category == 'test'
        assert test.ok is True
        assert test.directive.reason == 'No items in the list'
        assert test.skip is True
        assert test.todo is False

    def test_diagnostic(self, run_playbook, parser):
        result = run_playbook('test_diagnostic.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        diagnostics = lines[1:3]
        assert diagnostics[0].category == 'diagnostic'
        assert diagnostics[0].text == '# stat: setup (1)'
        assert diagnostics[1].category == 'diagnostic'
        assert diagnostics[1].text == '# stat: setup (2)'

    def test_multiple_with_failures(self, run_playbook, parser):
        result = run_playbook('test_multiple_with_failures.yml')
        lines = list(parser.parse_text(result.stdout.str()))
        plan = lines[-1]
        assert result.ret == 2
        assert plan.category == 'plan'
        assert plan.expected_tests == 5
