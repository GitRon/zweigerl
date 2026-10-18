# Mocking

**Mocking first-party code is strongly discouraged.** It is a last resort, not a technique to reach for
when a test is awkward to set up.

- A mock of our own code asserts that a particular function was called in a particular way — it pins the
  implementation, so the test goes green while the behaviour is broken and stays green through a refactor
  that breaks it. It tests the wiring you wrote down, not the wiring that runs.
- The usual reason to want one is expensive or fiddly setup. That is what [factories](testing-data.md) are
  for. Build the real objects and call the real code.
- If you still think you need one, the more likely reading is that the testee does too much. Split it and
  test the parts directly.
- When you genuinely cannot avoid it, leave a comment saying why. A first-party mock without a stated
  reason is a review finding.

## Boundaries are fair game

Mocking at the **boundary** is fine and expected: time, randomness, the filesystem outside the test's
temporary directory, network, third-party calls.

Two boundaries Zweigerl will have in particular:

- **Time.** "Zuletzt gesichert: vor 2 Tagen" and the backup folder's timestamp depend on the clock. Patch
  the clock in the module that reads it, see [spelling](#spelling), rather than asserting on today.
- **Files.** Uploads, imports and backups write files. Point them at pytest's `tmp_path` through
  `override_settings` instead of mocking the writes.

The pen-stroke lines of the tree (#11) are random only in appearance: they take a fixed seed per line, so
they need no patching.

## Spelling

Import as `from unittest import mock` and always spell it `mock.patch(...)`, never
`from unittest.mock import patch`. One consistent spelling across the suite.

Patch the name **where it is used**, not where it is defined. A module that imports
`from django.utils.timezone import now` is patched as
`mock.patch("apps.stammbaum.actions.sicherung.now", return_value=...)`. Patching
`django.utils.timezone.now` instead moves the clock for everything in the test, session expiry and
`auto_now` fields included; patching `...sicherung.timezone.now` in a module that imports the
`timezone` module is the same global patch under a longer name.

Always pass `return_value` when the patched call feeds an expression. Without it the call returns a
`MagicMock`, and most of what a test does with it passes silently: arithmetic returns another
`MagicMock` and `==` is simply `False`. Only an ordering comparison (`<`, `>`) raises.
