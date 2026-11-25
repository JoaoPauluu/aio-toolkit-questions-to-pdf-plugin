import re

import pytest
import yaml

from conftest import ROOT
from qtopdf.build import BuildError, list_templates, load_template

MANIFEST = yaml.safe_load((ROOT / "plugin.yaml").read_text(encoding="utf-8"))
INPUTS = {i["name"]: i for i in MANIFEST["inputs"]}


@pytest.mark.parametrize("name", list_templates())
def test_template_passes_contract(name):
    load_template(name)


def test_manifest_lists_exactly_the_templates():
    options = [o["value"] if isinstance(o, dict) else o for o in INPUTS["template"]["options"]]
    assert sorted(options) == list_templates()
    assert INPUTS["template"]["default"] in options


def test_run_py_reads_only_declared_params():
    # Same rule as AIO Toolkit's TestBuiltinPluginsAPIParity: undeclared params can't be set via the API.
    read = re.findall(r"""\bp(?:arams)?(?:\.get\(|\[)["']([a-z_][a-z0-9_]*)["']""", (ROOT / "run.py").read_text())
    assert read and set(read) <= INPUTS.keys(), set(read) - INPUTS.keys()


def test_missing_template():
    with pytest.raises(BuildError, match="not found"):
        load_template("nope")
