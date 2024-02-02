from __future__ import annotations

import os
import re
import sys

from isa import Code, DataTerm, Opcode, SourceTerm, StatementTerm, write_code


def avaliable_sections() -> dict[str, str]:
    return {".data": "section .data", ".text": "section .text"}

def symbols() -> set[str]:
    """ Полное множество символов, доступных к использованию в языке.

    Используется для парсинга секций данных и определения способа адресации лейблов.
    """
    return {":", "*", ",", ";", "'", '"'}


def instructions() -> set[str]:
    """ Полное множество команд, доступных к использованию в языке. """
    return {opcode.name.lower() for opcode in Opcode}

def map_instruction_to_opcode(instruction: str) -> Opcode | None:
    """ Отображение команд исходного кода в коды операций. """
    return {
        "ld": Opcode.LD,
        "st": Opcode.ST,
        "out": Opcode.OUT,
        "in": Opcode.IN,
        "add": Opcode.ADD,
        "sub": Opcode.SUB,
        "cmp": Opcode.CMP,
        "inc": Opcode.INC,
        "dec": Opcode.DEC,
        "mul": Opcode.MUL,
        "div": Opcode.DIV,
        "or": Opcode.OR,
        "and": Opcode.AND,
        "jmp": Opcode.JMP,
        "jz": Opcode.JZ,
        "jnz": Opcode.JNZ,
        "jn": Opcode.JN,
        "jnn": Opcode.JNN,
        "int": Opcode.INT,
        "eni": Opcode.ENI,
        "dii": Opcode.DII,
        "hlt": Opcode.HLT
    }.get(instruction)


def try_convert_str_to_int(num: str) -> int | None:
    try:
        return int(num)
    except ValueError:
        return None

def split_by_spec_symbols(elem: str) -> list[str]:
        tmp: list[str] = re.split(r"(\:|\;|\,|\*)+", elem)
        while "" in tmp:
            tmp.remove("")
        return tmp

def filter_comments_on_line(terms: list[str]) -> list[str]:
    term_num: int
    comment_start: int | None = None
    for term_num, term in enumerate(terms):
        if term == ";":
            comment_start = term_num
            break
    if comment_start is not None:
        terms = terms[:comment_start]
    return terms

def join_string_literals(terms: list[str]) -> list[str]:
    stack_quotes: list[str] = []
    tmp: list[str] = []
    common: list[str] = []
    indices: list[int] = []
    for term_num, term in enumerate(terms):
        if '"' in term: # упрощенная обработка разных кавычек
            stack_quotes.append("'")
            tmp.append(term)
            indices.append(term_num)
        else:
            common.append(term)
    if len(stack_quotes) > 0:
        assert len(stack_quotes) % 2 == 0, "String literals are incomplete."
        assert stack_quotes.pop() == stack_quotes.pop(), "Quotes at some string literal are different." # упрощенная валидация
        literal: str = " ".join(tmp)
        common.insert(indices[0], literal)
    return common


def split_programm_line_to_terms(line: str) -> list[str]:
    terms: list[str]
    complete_terms: list[str] = []
    line = line.strip()
    terms = line.split()
    tmp: list[str]
    for term in terms:
        tmp = split_by_spec_symbols(term)
        complete_terms.extend(tmp)
    return join_string_literals(complete_terms)


def split_text_to_source_terms(programm_text: str) -> list[SourceTerm]:
    source_terms: list[SourceTerm] = []
    term_line: list[str] = []
    # Нумерация строк исходного кода
    for line_num, line in enumerate(programm_text.split("\n"), 1):
        term_line = split_programm_line_to_terms(line)
        term_line = filter_comments_on_line(term_line)
        if len(term_line) == 0:
            continue
        source_terms.append(SourceTerm(line_num, term_line))
    return source_terms

def select_sections_terms(section_source_terms: list[SourceTerm]) -> list[SourceTerm]:
    """Поиск строк-термов, содержащих ключевое слово 'sections'."""
    return [term for term in section_source_terms if "section" in term.terms]


def validate_section_name(section_definition: SourceTerm) -> str:
    """Проверка имени секции. Возвращает имя секции."""
    assert len(section_definition.terms) >= 3, "Sections definition should contain 3 terms, line: {}.".format(section_definition.line)
    section_found: bool = False
    section_name: str | None = None

    for term_num, term in enumerate(section_definition.terms):
        match term_num:
            case 0:
                assert term == "section", "Section definition doesn't have 'section' keyword in place."
                assert not section_found, "Multiple section defenitions in line: {}.".format(section_definition.line)
                section_found = True
                continue
            case 1:
                assert term in avaliable_sections().keys(), "Unavaliable section name: {}, line: {}.".format(term, section_definition.line)
                section_name = term
                continue
            case 2:
                assert term == ":", "Section name should be followed by colon, line:{}.".format(section_definition.line)
                continue
            case 3:
                assert term == ";", "Section definition could be followed only by comment."
            case _:
                continue
    assert section_name is not None, "Section name not found, line: {}.".format(section_definition.line)
    return section_name

def validate_section_names(section_source_terms: list[SourceTerm]) -> bool:
    unique_avaliable_sections: set[str] = set()
    for source_term in section_source_terms:
        section_name: str = validate_section_name(source_term)
        assert section_name not in unique_avaliable_sections, "Section name should be unique: {}.".format(source_term.line)
        if section_name in unique_avaliable_sections:
            return False
        unique_avaliable_sections.update(section_name)
    return True

def split_source_terms_to_sections(programm_text_split: list[SourceTerm]) -> dict[str, list[SourceTerm]]:
    """ Разделение исходного кода программы по секциям для отдельной обработки.

    Возвращаемые значения в словаре:
    - сокращенное имя секции .data и термы строк
    - сокращенное имя секции .text и термы строк
    """
    sections: dict[str, list[SourceTerm]] = dict()
    sections_starts: dict[str, tuple[int, SourceTerm]] = dict()

    # Находим все секции и проверяем их объявления на корректность.
    section_expressions: list[SourceTerm] = select_sections_terms(programm_text_split)
    assert len(section_expressions) > 0, "No sections in programm."
    assert validate_section_names(section_expressions), "Section definition is not correct"

    # Сохраняем термы исходгого кода с порядковыми номерами после фильтрации от комментариев
    terms_by_line: list[tuple[int, SourceTerm]] = [(term_num, term) for term_num, term in enumerate(programm_text_split)]

    # Cохраняем начала доступных секций.
    for section in section_expressions:
        section_start: int | None = None
        for term in terms_by_line:
            if section == term[1]:
                section_start = term[0]
        assert section_start is not None, "Section start is not found"
        sections_starts[section.terms[1]] = (section_start, section)

    # Добавляем каждой секции в выходной структуре её содержимое без заголовка секции
    prev_name: str | None = None
    prev_pos: int | None = None
    prev_source_term: SourceTerm | None = None
    section_programm_start: int
    section_programm_end: int
    for name, pos_term in sections_starts.items():
        if prev_name is not None and prev_pos is not None and prev_source_term is not None:
            section_programm_start = prev_pos + 1
            section_programm_end = pos_term[0]
            sections[prev_name] = [pos_term[1] for pos_term in terms_by_line[section_programm_start : section_programm_end]]
        prev_name = name
        prev_pos = pos_term[0]
        prev_source_term = pos_term[1]
    assert prev_name is not None
    assert prev_pos is not None
    assert prev_source_term is not None
    section_programm_start = prev_pos + 1
    sections[prev_name] = [pos_term[1] for pos_term in terms_by_line[section_programm_start : ]]

    return sections

def match_label(term: SourceTerm) -> str | None:
    """ Проверка строки SourceTerm на наличие лейбла.

    Возвращает имя лейбла при наличии и None иначе.
    """
    line: list[str] = term.terms
    # Проверка: есть ли в строке исходного кода двоеточие
    try:
        line.index(":")
    except ValueError:
        return None
    assert len(line) >= 2 and line[1] == ":", "Label name is not correct, line: {}".format(term.line)  # noqa: PT018
    assert line[0] not in instructions(), "Label name can't be instructuction name, line: {}".format(term.line)
    res = re.fullmatch(r"[a-zA-Z_][\w]*", line[0], 0)
    assert res is not None, "Label name doesn't match requirements"
    return line[0]


def map_text_to_instructions(command_section_terms: list[SourceTerm], data_labels: dict[str, int]) -> list[StatementTerm]:
    """ Трансляция тескта секции инструкций исходной программы в последовательность термов команд.

    Проверяется корректность аргументов, соответствие лейблов данных параметрам инструкций данных
    и уникальность и соответствие лейблов инструкций параметрам инструкций контроля выполнения.
    """
    found_labels: set[str] = set()
    terms: list[StatementTerm] = []
    cur_label: str | None = None
    for instruction_counter, term in enumerate(command_section_terms):
        cur_label = match_label(term)
        found_labels.add(cur_label) if cur_label is not None and cur_label not in found_labels else found_labels

    return terms

def map_text_to_data(data_section_terms: list[SourceTerm]) -> tuple[list[DataTerm], dict[str, int]]:
    """ Трансляция текста секции данных исходной программы в последовательность термов данных.

    Проверяются лейблы и корректность объявления данных.
    Возвращаемые значения:
    - список термов данных в программе
    - словарь имён лейблов данных и их адресов, согласно длине данных
    """
    labels: set[str] = set()
    data_terms: list[DataTerm] = []
    labels_addr: dict[str, int] = dict()
    instruction_counter: int = 0
    for term_num, term in enumerate(data_section_terms, 1):
        cur_label: str | None = match_label(term)
        data_size: int | None = None
        value: int | str | None = None
        assert cur_label is not None, "Failed to translate: Data declaration or definition can't be done without label, line: {}".format(term.line)
        assert cur_label not in labels, "Failed to translate: labels in section .bss are not unique. section data -> line: {}".format(term.line)
        labels.add(cur_label)
        data_size = try_convert_str_to_int(term.terms[2])
        assert data_size is not None, "Failed to translate: data size should be non-negative int value, line: {}".format(term.line)

        match len(term.terms):
            case 4: # Data declaration
                pass
            case 5: # Data defenition
                value = term.terms[4][1:-1]
            case _:
                raise AssertionError("Data term doen't fit declaration or definition rules, line: {}".format(term.line))

        data_term: DataTerm = DataTerm(index = instruction_counter, label = cur_label, line = term.line, value = value)
        data_terms.append(data_term)
        labels_addr[cur_label] = instruction_counter
        instruction_counter += data_size
    return (data_terms, labels_addr)

def translate(code_text: str) -> Code:
    """ Трансляция текста исходной программы в машинный код для процессора.

    В процессе трансляции сохраняются адреса лейблов данных и кода для подстановки адресов.
    """
    code: Code
    section_data: list[SourceTerm] | None = None
    section_text: list[SourceTerm] | None = None
    # code_labels: dict[str, int] = {}
    data_labels: dict[str, int] = {}
    code_terms: list[StatementTerm] = []
    data_terms: list[DataTerm] = []

    source_terms: list[SourceTerm] = split_text_to_source_terms(code_text)
    sections: dict[str, list[SourceTerm]] = split_source_terms_to_sections(source_terms)

    section_text = sections.get(".text")
    assert section_text is not None, "Failed to translate: Section .text is not present in program"
    section_data = sections.get(".data")
    if section_data is not None:
        data_terms, data_labels = map_text_to_data(section_data)

    data_terms, data_labels = map_text_to_data(section_data)
    code_terms = map_text_to_instructions(section_text, data_labels)




    for adress, statement in enumerate(code_terms, 1):
        pass

    return code



def main(source_code_file_name: str, target_file_name: str) -> None:
    """ Функция запуска транслятора.

    Параметры:
    - Файл с исходным кодом программы.
    - Файл, в который в случае успеха трансляции будет записан машинный код.
    """
    with open(source_code_file_name, encoding="utf-8") as f:
        source = f.read()

    code: Code = translate(source)

    write_code(target_file_name, code)
    print("source LoC:", len(source.split("\n")), "code instr:", len(code.contents))

if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments. Correct way is: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)

