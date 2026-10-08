# The login wall (app/core/auth.py) is switched OFF for the existing test-suite,
# which talks to the API directly; tests/test_auth.py switches it on itself.
import os

os.environ.setdefault("AUTH_DISABLED", "1")
