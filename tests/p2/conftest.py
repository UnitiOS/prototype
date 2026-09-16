"""Package-writing tests point the Studio write gate at their own directory.

The gate refuses to write outside its packages root — that is the whole of its
containment — so a test that writes into a temp directory says so rather than
asking the gate to make an exception.
"""

import os
import tempfile
from contextlib import contextmanager


@contextmanager
def package_sandbox():
    """A temp directory that is, for its lifetime, the gate's packages root."""
    previous = os.environ.get("UNITI_PACKAGES_ROOT")
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["UNITI_PACKAGES_ROOT"] = tmp_dir
        try:
            yield tmp_dir
        finally:
            if previous is None:
                os.environ.pop("UNITI_PACKAGES_ROOT", None)
            else:
                os.environ["UNITI_PACKAGES_ROOT"] = previous
