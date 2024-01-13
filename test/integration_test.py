import contextlib
import io
import logging
import os
import sys
import tempfile

import pytest


@pytest.mark.golden_test("golden_tests/integration/*.yml")
def test_translator_and_machine(golden, caplog) -> void:
    """ Golden tests для транслятора и модели компьютера.
    """
    