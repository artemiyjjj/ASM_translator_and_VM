import contextlib
import io
import logging
import os
import tempfile

import pytest
import unittest

from isa import read_code, write_code, MachineWordData, MachineWordInstruction, SourceTerm
from translator import (
    validate_section_name,
    map_terms_to_data,
    match_label,
    split_text_to_source_terms,
    split_programm_line_to_terms,
)
from machine import DataPath, ControlUnit, Machine, DataBus, InterruptionLine


@pytest.mark.golden_test("golden_tests/unit/translator_validate_sections.yml")
def test_translator_section_name_validation(golden: str, caplog) -> None:
    """Golden tests разделения текста программы на секции."""

    def get_section_name_if_correct(line):
        terms: list[str] = split_text_to_source_terms(line)
        return validate_section_name(terms[0])

    assert get_section_name_if_correct(golden["in_correct_def1"]) == golden.out["out_correct_def1"]
    assert get_section_name_if_correct(golden["in_correct_def2"]) == golden.out["out_correct_def2"]
    assert get_section_name_if_correct(golden["in_correct_def3"]) == golden.out["out_correct_def3"]

    with pytest.raises(AssertionError) as e:
        get_section_name_if_correct(golden["in_missed_dot"])
    assert str(e.value) == golden.out["out_missed_dot"]

    with pytest.raises(AssertionError) as e:
        get_section_name_if_correct(golden["in_not_only_section_def"])
    assert str(e.value) == golden.out["out_not_only_section_def"]

    with pytest.raises(AssertionError) as e:
        get_section_name_if_correct(golden["in_missed_semicolon"])
    assert str(e.value) == golden.out["out_missed_semicolon"]

    with pytest.raises(AssertionError) as e:
        get_section_name_if_correct(golden["in_not_correct_name"])
    assert str(e.value) == golden.out["out_not_correct_name"]


@pytest.mark.golden_test("golden_tests/unit/translator_label_matching.yml")
def test_translator_text_label_matching(golden: str, caplog) -> None:
    """Golden tests создания термов команд в трансляторе."""

    def split_and_match(text: str):
        terms_list: list[SourceTerm] = split_text_to_source_terms(text)
        return match_label(terms_list[0])

    assert split_and_match(golden["in_label_correct_ordinary1"]) == golden.out["out_label_correct_ordinary1"]
    assert split_and_match(golden["in_label_correct_ordinary2"]) == golden.out["out_label_correct_ordinary2"]
    assert (
        split_and_match(golden["in_label_correct_followed_by_instruction"])
        == golden.out["out_label_correct_followed_by_instruction"]
    )

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_label_incorrect_number"])
    assert str(e.value) == golden.out["out_label_incorrect_number"]

    assert split_and_match(golden["in_label_no_label"]) == golden.out["out_label_no_label"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_label_name_instruction"])
    assert str(e.value) == golden.out["out_label_name_instruction"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_label_name_multiple_words"])
    assert str(e.value) == golden.out["out_label_name_multiple_words"]


@pytest.mark.golden_test("golden_tests/unit/translator_data_terms.yml")
def test_translator_data_label_matching(golden: str, caplog) -> None:
    """Golden tests создания термов данных в трансляторе."""

    def split_and_match(text: str):
        terms_list: list[str] = split_text_to_source_terms(text)
        data_terms, _ = map_terms_to_data(terms_list)
        return data_terms

    assert split_and_match(golden["in_correct_data_term1"])[0].label == golden.out["out_correct_data_term1"]
    assert split_and_match(golden["in_correct_data_term2"])[0].label == golden.out["out_correct_data_term2"]
    assert split_and_match(golden["in_correct_data_term3"])[0].label == golden.out["out_correct_data_term3"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_same_labels"])
    assert str(e.value) == golden.out["out_same_labels"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_no_label"])
    assert str(e.value) == golden.out["out_no_label"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_incorrect_size1"])
    assert str(e.value) == golden.out["out_incorrect_size1"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_incorrect_size2"])
    assert str(e.value) == golden.out["out_incorrect_size2"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_incorrect_size3"])
    assert str(e.value) == golden.out["out_incorrect_size3"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_no_size"])
    assert str(e.value) == golden.out["out_no_size"]

    with pytest.raises(AssertionError) as e:
        split_and_match(golden["in_extra_size"])
    assert str(e.value) == golden.out["out_extra_size"]


@pytest.mark.golden_test("golden_tests/unit/translator_filter_comments.yml")
def test_translator_filter_comments(golden: str, caplog) -> None:
    """Golden tests способности транслятора фильтровать комментарии."""
    assert split_programm_line_to_terms(golden["in_code_after"]).__repr__() == golden.out["out_code_after"]
    assert split_programm_line_to_terms(golden["in_code_before"]).__repr__() == golden.out["out_code_before"]
    assert (
        split_programm_line_to_terms(golden["in_code_after_section"]).__repr__() == golden.out["out_code_after_section"]
    )
    assert split_programm_line_to_terms(golden["in_code_two_coments"]).__repr__() == golden.out["out_code_two_comments"]
    assert split_programm_line_to_terms(golden["in_incorrect_label"]).__repr__() == golden.out["out_incorrect_label"]


@pytest.mark.golden_test("golden_tests/unit/machine_data_path.yml")
def test_machine_alu(golden: str, caplog) -> None:
    """Golden tests АЛУ в DataPath компьютера."""
    alu: DataPath.ALU = DataPath.ALU()

    def reset_regs():
        alu._left_register = golden["in_value1"]
        alu._right_register = golden["in_value2"]

    alu.negative(mode=0)
    assert alu._left_register == golden.out["out_neg"]
    alu.inc(mode=1)
    assert alu._right_register == golden.out["out_inc"]
    alu.dec(mode=1)
    assert alu._right_register == golden.out["out_dec"]
    reset_regs()
    alu.operation(mode=0)
    assert alu._output_buffer_register == golden.out["out_add"]
    reset_regs()
    alu.operation(mode=1)
    assert alu._output_buffer_register == golden.out["out_sub"]
    reset_regs()
    alu.operation(mode=2)
    assert alu._output_buffer_register == golden.out["out_mul"]
    reset_regs()
    alu.operation(mode=3)
    assert alu._output_buffer_register == golden.out["out_div"]
    reset_regs()
    alu.operation(mode=4)
    assert alu._output_buffer_register == golden.out["out_mod"]
    reset_regs()
    alu.operation(mode=5)
    assert alu._output_buffer_register == golden.out["out_and"]
    reset_regs()
    alu.operation(mode=6)
    assert alu._output_buffer_register == golden.out["out_or"]
    reset_regs()
    alu.operation(mode=7)
    assert alu._output_buffer_register == golden.out["out_shift_left"]
    reset_regs()
    alu.operation(mode=8)
    assert alu._output_buffer_register == golden.out["out_shift_right"]
