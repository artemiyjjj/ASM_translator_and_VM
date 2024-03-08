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


# @pytest.mark.golden_test("golden_tests/integration/.yml")
# def test_translator_and_isa(golden, caplog) -> None:\
#     """Golden tests для транслятора и системы команд."""

@pytest.mark.golden_test("golden_tests/integration/hello.yml")
def test_executing_example_hello(golden, caplog) -> None:
    """Golden tests для программы 'hello' и модели компьютера."""
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdir1:
        source = os.path.join(tmpdir1, "code1.asm")
        binary = os.path.join(tmpdir1, "target1.bin")
        schedule = os.path.join(tmpdir1, "schedule1")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_program"])

        with open(schedule, "w", encoding="utf-8") as file_schedule:
            file_schedule.write("")

        translator.main(source, binary)
        translator_out = caplog.text
        caplog.clear()
        
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            machine.main(binary, schedule)

        with open(binary, encoding="utf-8") as file:
            code = file.read()

        assert translator_out == golden.out["out_translator_log"]
        assert code == golden.out["out_code"]
        assert stdout.getvalue() == golden.out["out_machine_output"]
        assert caplog.text == golden.out["out_machine_log"]
        

@pytest.mark.golden_test("golden_tests/integration/cat.yml")
def test_executing_example_cat(golden, caplog) -> None:
    """Golden tests для программы 'cat' и модели компьютера."""
    # Установим уровень отладочного вывода на DEBUG
    caplog.set_level(logging.DEBUG)

    # Создаём временную папку для тестирования приложения.
    with tempfile.TemporaryDirectory() as tmpdir:
        # Готовим имена файлов для входных и выходных данных.
        source = os.path.join(tmpdir, "code.asm")
        binary = os.path.join(tmpdir, "target.bin")
        input_schedule = os.path.join(tmpdir, "input_schedule")

        # Записываем входные данные в файлы. Данные берутся из теста.
        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_program"])
        
        with open(input_schedule, "w", encoding="utf-8") as file_schedule:
            file_schedule.write(golden["in_shcedule"])

        translator.main(source, binary)
        translator_out = caplog.text
        caplog.clear()
        
        # Запускаем транслятор и собираем весь стандартный вывод в переменную stdout
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            machine.main(binary, input_schedule)

        # Выходные данные транслятора считываем в переменную.
        with open(binary, encoding="utf-8") as file:
            code = file.read()

        # Проверяем соответсвие результатов golden test'ам.
        assert translator_out == golden.out["out_translator_log"]
        assert code == golden.out["out_code"]
        assert stdout.getvalue() == golden.out["out_machine_output"]
        assert caplog.text == golden.out["out_machine_log"]





@pytest.mark.golden_test("golden_tests/integration/prob1.yml")
def test_executing_example_prob(golden, caplog) -> None:
    """Golden tests для программы 'prob' и модели компьютера."""
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdir2:
        source = os.path.join(tmpdir2, "code2.asm")
        binary = os.path.join(tmpdir2, "target2.bin")
        schedule = os.path.join(tmpdir2, "schedule2")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_program"])

        with open(schedule, "w", encoding="utf-8") as file_schedule:
            file_schedule.write("")

        translator.main(source, binary)
        translator_out = caplog.text
        caplog.clear()
        
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            machine.main(binary, schedule)

        with open(binary, encoding="utf-8") as file:
            code = file.read()

        # Преобразуем байты, представленные машиной в формате unicode, в 4 байтовое число
        result: int = int.from_bytes([ord(elem) for elem in stdout.getvalue()], byteorder='big')

        assert translator_out == golden.out["out_translator_log"]
        assert code == golden.out["out_code"]
        assert result == golden.out["out_machine_output"]
        assert caplog.text == golden.out["out_machine_log"]

    