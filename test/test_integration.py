import contextlib
import io
import logging
import os
import sys
import tempfile

import pytest

import isa
import machine
import translator


@pytest.mark.golden_test("golden_tests/integration/*.yml")
def test_executing_example_programm(golden, caplog) -> None:
    """Golden tests для всех программ и модели компьютера."""
    caplog.set_level(logging.INFO)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, "code1.asm")
        binary = os.path.join(tmpdir, "target1.bin")
        sched = os.path.join(tmpdir, "schedule1")
        input = os.path.join(tmpdir, "input")

        with open(input, "w", encoding="utf-8") as input_file:
            input_file.write(golden["stdin"])

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_program"])

        with open(sched, "w", encoding="utf-8") as file_schedule:
            schedule = golden["in_schedule"] if golden["in_schedule"] is not None else ""
            file_schedule.write(schedule)

        translator.main(source, binary)
        translator_log = caplog.text
        caplog.clear()

        if golden["stdin"] != "":
            sys.stdin = open(input, "r", encoding="utf-8")

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            machine.main(binary, sched)

        with open(binary, encoding="utf-8") as file:
            code = file.read()

        if golden["in_is_output_number"] == "1":
            result = int.from_bytes([ord(elem) for elem in stdout.getvalue()], byteorder="big")
        else:
            result = stdout.getvalue()

        assert translator_log == golden.out["out_translator_log"]
        assert code == golden.out["out_code"]
        assert result == golden.out["out_machine_output"]
        assert caplog.text == golden.out["out_machine_log"]
        if golden["stdin"] != "":
            sys.stdin.close()
