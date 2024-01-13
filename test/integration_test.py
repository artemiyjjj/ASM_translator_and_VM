import contextlib
import io
import logging
import os
import sys
import tempfile

import pytest


@pytest.mark.golden_test("golden_tests/integration/*.yml")
def test_translator_and_isa(golden, caplog) -> None:
    """ Golden tests для транслятора и системы команд. """


@pytest.mark.golden_test("golden_tests/integration/*.yml")
def test_translator_and_machine(golden, caplog) -> None:
    """ Golden tests для транслятора и модели компьютера. """
