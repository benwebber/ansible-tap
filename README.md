# ansible-tap

[Test Anything Protocol (TAP)](https://testanything.org/) producer for Ansible.

This callback plugin allows you to write TAP test suites as Ansible playbooks. Consider it an Ansible-only alternative to [Serverspec](http://serverspec.org/) and [Testinfra](https://testinfra.readthedocs.io/).

## Install

While you can't install this plugin directly using `ansible-galaxy`, you can use `ansible-galaxy` to download it:


```
ansible-galaxy install https://github.com/benwebber/ansible-tap.git
```

Copy or link the plugin itself to `~/.ansible/plugins/callback`:

```
mkdir -p ~/.ansible/plugins/callback
ln -s /etc/ansible/roles/benwebber.tap/library/callback_plugins/tap.py ~/.ansible/plugins/callback/tap.py
```

## Usage

Configure Ansible to use this plugin as the standard output callback:

```
ANSIBLE_STDOUT_CALLBACK=tap ansible-playbook -i hosts test.yml -l hostname
```

## Writing Ansible tests

By default, Ansible will abort the play if any tasks fail. Set `ignore_errors: true` on all tests to disable this behaviour:

```yaml
- name: check if service is running
  command: systemctl is-active service
  register: is_active
  tags: diagnostic

- name: assert that service is running
  assert:
    that: is_active.rc == 0
  ignore_errors: true
```

This will ensure Ansible executes the entire test suite, barring any unexpected failure.

If a task fails, the plugin will output troubleshooting information as an embedded [YAML document](https://testanything.org/tap-version-13-specification.html#yaml-blocks):

```tap
not ok - assert: assert that variable is set
  ---
  _ansible_no_log: false
  _ansible_verbose_always: true
  assertion: status is defined
  changed: false
  evaluated_to: false
  failed: true
  invocation:
    module_args:
      that: status is defined
    module_name: assert
  ...
```

### Excluding tasks from TAP stream

Often, the result of a test will depend on previous tasks. You will naturally want to exclude these setup tasks from the TAP stream.

To do so, simply tag setup tasks with the `diagnostic` tag:

```yaml
- name: set up next test
  command: 'true'
  register: true_
  tags: diagnostic

- name: should always pass
  assert:
    that: true_.rc == 0
  ignore_errors: true
```

The callback plugin will print diagnostic lines instead of test lines:

```tap
# command: set up next test
ok - assert: should always pass
````

Unlike individual test cases, you probably do not want to ignore errors for this type of task. Failures would represent an error in the test suite and not a test failure.

### Expected failures and unexpected successes

TAP supports a `TODO` directive to ignore tests for features that haven't been implemented yet.

If a test marked with `TODO` fails, TAP consumers will consider it an expected failure. Similarly, if a test marked with `TODO` passes, TAP consumers will consider it an unexpected success.

Tag expected failures with `TODO`:

```yaml
- name: expected failure
  assert:
    that: false
  ignore_errors: true
  tags: TODO
```

This will output a `# TODO` directive in TAP stream:

```tap
not ok - assert: expected failure # TODO
```

If the test passes, you'll receive unexpected success output:

```tap
ok - assert: expected failure # TODO
```

### Skipping tests

TAP also supports a `SKIP` directive to ignore specific tests.

This callback uses Ansible's `when` statement to control skipped tests:

```yaml
- name: this is a skipped task
  assert:
    that: false
  ignore_errors: true
  when: false
```

The reason for skipping the test will appear in the test line:

```tap
ok - assert: skipped # SKIP Conditional check failed
```

## Example

The [`tests/`](tests/) directory contains an example test suite which produces all possible test results.

After installing the plugin, run the test suite with:

```
ANSIBLE_STDOUT_CALLBACK=tap ansible-playbook -i localhost, -c local test.yml
```

You will receive the following TAP stream. You can pass this to any TAP consumer.

```tap
TAP version 13
# command: set up next test
ok - assert: pass
not ok - assert: failed
  ---
  _ansible_no_log: false
  _ansible_verbose_always: true
  assertion: false
  changed: false
  evaluated_to: false
  failed: true
  invocation:
    module_args:
      that: false
    module_name: assert
  ...
not ok - assert: expected failure # TODO
ok - assert: unexpected pass # TODO
ok - assert: skipped # SKIP Conditional check failed
1..5
```

## Caveats

At present, this plugin only supports running tests against a single host at a time. The TAP specification does not describe a way to combine multiple output streams.

## License

MIT
