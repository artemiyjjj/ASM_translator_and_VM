import contextlib
import io
import logging
import os
import tempfile

import pytest

from isa import read_code, write_code
from translator import match_label, split_text_to_source_terms


# @pytest.mark.golden_test("golden_tests/unit/isa.yml")
# def test_isa(golden: str, caplog) -> None:
#     """Golden tests модели системы команд."""
#     # Установим уровень отладочного вывода на DEBUG
#     caplog.set_level(logging.DEBUG)

#     # Создаём временную папку для тестирования приложения.
#     with tempfile.TemporaryDirectory() as tmpdirname:
#         # Готовим имена файлов для входных и выходных данных.
#         source = os.path.join(tmpdirname, "binary_code.o")
#         target = os.path.join(tmpdirname, "target.o")

#         # Записываем входные данные в файлы. Данные берутся из теста.
#         with open(source, "w", encoding="utf-8") as file:
#             file.write(golden["in_code"])

#         # Запускаем транслятор и собираем весь стандартный вывод в переменную
#         # stdout
#         with contextlib.redirect_stdout(io.StringIO()) as stdout:
#             code = read_code(source)
#             print(code)
#             write_code(target, code)

#         # Выходные данные также считываем в переменные.
#         with open(target, encoding="utf-8") as file:
#             code = file.read()

#         # Проверяем, что ожидания соответствуют реальности.
#         assert code == golden.out["out_code"]
#         assert stdout.getvalue() == golden.out["out_obj"]

#     @pytest.mark.golden_test("golden_tests/unit/translator.yml")
#     def test_translator_label_matching(golden: str, caplog) -> None:
#         """Golden tests транслятора."""
#         # таким образом вставлять тестовые случаи
#         # вывод - имя лейбла, None или ассерт: текст
#         match_label(split_text_to_source_terms("_start:")[0])

#     @pytest.mark.golden_test("golden_tests/unit/machine.yml")
#     def test_machine(golden: str, caplog) -> None:
#         """Golden tests модели компьютера."""
