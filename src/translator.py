from __future__ import annotations

import logging
import os
import re
import sys

from isa import Code, DataTerm, Mode, Opcode, SourceTerm, StatementTerm, write_code
from machine import get_interruption_vector_length, get_machine_start_addr


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
        "mod": Opcode.MOD,
        "or": Opcode.OR,
        "and": Opcode.AND,
        "lsl": Opcode.LSL,
        "asr": Opcode.ASR,
        "jmp": Opcode.JMP,
        "jz": Opcode.JZ,
        "jnz": Opcode.JNZ,
        "jn": Opcode.JN,
        "jp": Opcode.JP,
        "int": Opcode.INT,
        "fi": Opcode.FI,
        "eni": Opcode.ENI,
        "dii": Opcode.DII,
        "hlt": Opcode.HLT,
        "nop": Opcode.NOP
    }.get(instruction)


def try_convert_str_to_int(num: str) -> int | None:
    try:
        return int(num)
    except ValueError:
        return None

def split_by_spec_symbols(elem: str) -> list[str]:
        tmp: list[str] = re.split(r"(\:|\;|\,|\*)", elem)
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

def count_inverted_commas(term: str) -> int:
    ic_amount: int = 0
    for symb in term:
        if symb == '"':
            ic_amount += 1
    return ic_amount

def join_string_literals(terms: list[str]) -> list[str]:
    stack_quotes: list[str] = []
    tmp: list[str] = []
    common: list[str] = []
    indices: list[int] = []
    for term_num, term in enumerate(terms):
        if '"' in term: # упрощенная обработка разных кавычек
            stack_quotes.append("'")
            if count_inverted_commas(term):
                stack_quotes.append("'")
            tmp.append(term)
            indices.append(term_num)
        else:
            common.append(term)
    if len(stack_quotes) > 0:
        assert len(stack_quotes) % 2 == 0, "Translation failed: String literals are incomplete."
        assert stack_quotes.pop() == stack_quotes.pop(), "Translation failed: Quotes at some string literal are different." # упрощенная валидация
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
    assert len(section_definition.terms) >= 3, "Translation failed: Sections definition should contain 3 terms, line: {}.".format(section_definition.line)
    section_found: bool = False
    section_name: str | None = None

    for term_num, term in enumerate(section_definition.terms):
        match term_num:
            case 0:
                assert term == "section", "Translation failed: Section definition doesn't have 'section' keyword in place."
                assert not section_found, "Translation failed: Multiple section defenitions in line: {}.".format(section_definition.line)
                section_found = True
                continue
            case 1:
                assert term in avaliable_sections().keys(), "Translation failed: Unavaliable section name: {}, line: {}.".format(term, section_definition.line)
                section_name = term
                continue
            case 2:
                assert term == ":", "Translation failed: Section name should be followed by colon, line:{}.".format(section_definition.line)
                continue
            case 3:
                assert term == ";", "Translation failed: Section definition could be followed only by comment."
            case _:
                continue
    assert section_name is not None, "Translation failed: Section name not found, line: {}.".format(section_definition.line)
    return section_name

def validate_section_names(section_source_terms: list[SourceTerm]) -> bool:
    unique_avaliable_sections: set[str] = set()
    for source_term in section_source_terms:
        section_name: str = validate_section_name(source_term)
        assert section_name not in unique_avaliable_sections, "Translation failed: Section name should be unique: {}.".format(source_term.line)
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
    assert len(section_expressions) > 0, "Translation failed: No sections in programm."
    assert validate_section_names(section_expressions), "Translation failed: Section definition is not correct"

    # Сохраняем термы исходгого кода с порядковыми номерами после фильтрации от комментариев
    terms_by_line: list[tuple[int, SourceTerm]] = [(term_num, term) for term_num, term in enumerate(programm_text_split)]

    # Cохраняем начала доступных секций.
    for section in section_expressions:
        section_start: int | None = None
        for term in terms_by_line:
            if section == term[1]:
                section_start = term[0]
        assert section_start is not None, "Translation failed: Section start is not found"
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
    """ Проверка строки SourceTerm на наличие объявления лейбла.

    Возвращает имя лейбла при наличии и None иначе.
    """
    line: list[str] = term.terms
    # Проверка: есть ли в строке исходного кода двоеточие
    try:
        line.index(":")
    except ValueError:
        return None
    assert len(line) >= 2 and line[1] == ":", "Translation failed: Label name is not correct, line: {}".format(term.line)  # noqa: PT018
    assert line[0] not in instructions(), "Translation failed: Label name can't be instructuction name, line: {}".format(term.line)
    res = re.fullmatch(r"[a-zA-Z_][\w]*", line[0], 0)
    assert res is not None, "Translation failed: Label name doesn't match requirements"
    return line[0]

def select_remove_statement_mode(statement: SourceTerm) -> Mode:
    """ Проверка наличия оператора '*' в выражении

    Возвращает соответствующий режим интерпретации аргумента и его позицию в выражении при наличии. """
    mode: Mode
    symb_count: int = len([term for term in statement.terms if term == "*"])
    match symb_count:
        case 0:
            mode = Mode.VALUE
        case 1:
            mode = Mode.DIRECT
        case 2:
            mode = Mode.INDIRECT
        case _:
            raise AssertionError("Translation failed: too much deref symbols for 1 line, line: {}".format(statement.line))
    return mode

def validate_unary_operation_argument(statement: StatementTerm, operation_labels: set[str], data_labels: set[str]) -> int | str:
    """ Проверка аргументов инструкций с одним аргументом."""
    arg_term: int | str | None = statement.arg
    arg: int | str

    is_control_flow_operation: bool = statement.opcode in Opcode.control_flow_operations()
    is_data_manipulation_operation: bool = statement.opcode in Opcode.data_manipulation_operations()
    assert is_control_flow_operation ^ is_data_manipulation_operation, "Translation bug: ISA represents opcode '{}' incorrectly, line: {}".format(statement.opcode, statement.line)
    if is_control_flow_operation:
        assert arg_term in operation_labels, "Translation failed: control flow instruction argument should be an operation statement label, line: {}".format(statement.line)
        arg = arg_term
    elif is_data_manipulation_operation:
        assert arg_term not in operation_labels, "Translation failed: statement label provided to data manipulation instruction, line: {}".format(statement.line)
        # assert statement.opcode != Opcode.ST or statement.mode == Mode.VALUE, "Translation failed: store instruction argument should be address, line: {}".format(statement.line)
        arg = try_convert_str_to_int(arg_term)
        if arg is None:
            assert arg_term in data_labels, "Translation failed: data label in argument is not defined, line: {}".format(statement.line)
            arg = arg_term
    assert arg is not None
    return arg

def map_term_to_statement(statement: SourceTerm, instruction_counter: int, operation_labels: set[str], data_labels: set[str]) -> StatementTerm:
    """ Прербразование выражения текста исходной пргограммы в выражение машинного кода

    Преобразование проверяет соответствие аргумента типу операции и оставляет имена лейблов в аргументах.

    Возвращает
    - частичное выражение с лейблом, но без Opcode (когда в исходном коде лейбл отдельно от выражения)
    - обычное выражение без лейбла
    - обычное выражение с лейблом
    """
    statement_term: StatementTerm = StatementTerm(index = instruction_counter, line = statement.line)
    statement_term.label = match_label(statement)
    # Убираем имя лейбла из выражения при наличии
    if statement_term.label is not None:
        del statement.terms[:2]

    statement_term.mode = select_remove_statement_mode(statement)
    # Убираем символ косвенной адресации
    match statement_term.mode:
        case Mode.VALUE:
            pass
        case Mode.DIRECT:
            statement.terms.remove("*")
        case Mode.INDIRECT:
            statement.terms.remove("*")
            statement.terms.remove("*")

    instruction_name: str | None = statement.terms[0] if len(statement.terms) > 0 else None
    if instruction_name is not None:
        statement_term.opcode = map_instruction_to_opcode(instruction_name) if instruction_name is not None else None
        assert statement_term.opcode is not None, "Translation failed: instruction {} is not supported, line: {}".format(instruction_name, statement.line)
        is_unary_operation: bool = statement_term.opcode in Opcode.unary_operations()
        is_noop_operation: bool = statement_term.opcode in Opcode.no_operand_operations()
        assert is_unary_operation ^ is_noop_operation, "Translation bug: ISA represents opcode '{}' incorrectly, line: {}".format(statement_term.opcode, statement.line)
        if is_unary_operation:
            statement_term.arg = statement.terms[1] if len(statement.terms) >= 2 else None
            assert statement_term.arg is not None, "Translation failed: invalid unary opration argument, line: {}".format(statement.line)
            statement_term.arg = validate_unary_operation_argument(statement_term, operation_labels, data_labels)
        elif is_noop_operation:
            assert is_noop_operation and len(statement.terms) == 1, "Translation failed: instruction {} works without arguments, line: {}".format(statement_term.opcode, statement.line)  # noqa: PT018
            statement_term.mode = None
    return statement_term

def map_terms_to_statements(text_section_terms: list[SourceTerm], data_labels: set[str]) -> tuple[list[StatementTerm], dict[str, int]]:
    """ Трансляция тескта секции инструкций исходной программы в последовательность термов команд.

    Проверяется корректность аргументов, соответствие лейблов данных параметрам инструкций данных
    и уникальность и соответствие лейблов инструкций параметрам инструкций контроля выполнения.

    Возвращаемые значения:
    - список термов выражений в программе
    """
    instruction_counter: int = 0
    operation_labels: set[str] = set()
    labels_addr: dict[str, int] = dict()
    terms: list[StatementTerm] = []
    # Находим все выражения с лейблами
    for instruction_counter, statement in enumerate(text_section_terms):
        cur_label: str | None = match_label(statement)
        if cur_label is not None:
            operation_labels.add(cur_label) if cur_label not in operation_labels else operation_labels
            # Фиксируем адрес каждого выражения
            labels_addr[cur_label] = instruction_counter

    instruction_counter = 0
    prev_label: str | None = None
    for statement in text_section_terms:
        statement_term: StatementTerm = map_term_to_statement(statement, instruction_counter, operation_labels, data_labels)
        if prev_label is not None:
            assert statement_term.label is None, "Translation failed: statement shouldn't have more than 1 label, line: {}".format(statement.line)
            statement_term.label = prev_label
            prev_label = None
        if statement_term.opcode is None:
            prev_label = statement_term.label
            continue
        terms.append(statement_term)
        instruction_counter += 1
    logging.debug
    logging.debug("==========================")
    logging.debug("Code terms:")
    [logging.debug(term) for term in terms]
    logging.debug("==========================")
    logging.debug("Code labels indicies:")
    logging.debug(labels_addr)
    logging.debug("==========================")
    return (terms, labels_addr)

def map_literal_to_data_terms(data_term: DataTerm) -> list[DataTerm]:
    """ Трансляция терма данных, представляющего п-сторку, в последовательность термов данных - символов с размером строки."""
    terms: list[DataTerm] = []
    literal: str | list[int] = data_term.value if data_term.value is not None else [0] * data_term.size

    terms.append(DataTerm(
        index = data_term.index,
         label = data_term.label,
         value = data_term.size,
         size = None,
         line = data_term.line))
    print(data_term.value)
    for index, elem in enumerate(literal, 1):
        terms.append(DataTerm(
            index = data_term.index + index,
            label = "{}(+ {})".format(data_term.label, index),
            value = literal[index - 1],
            size = None,
            line = data_term.line))
        index += 1
    return terms

def map_terms_to_data(data_section_terms: list[SourceTerm]) -> tuple[list[DataTerm], dict[str, int]]:
    """ Трансляция последовательности термов секции данных исходной программы в последовательность термов данных.

    Проверяются лейблы и корректность объявления данных.

    Возвращаемые значения:
    - список термов данных в программе
    - словарь имён лейблов данных и их адресов, согласно длине данных
    """
    labels: set[str] = set()
    complete_data_terms: list[DataTerm] = []
    labels_addr: dict[str, int] = dict()
    data_index: int = 0
    for term in data_section_terms:
        cur_label: str | None = match_label(term)
        data_size: int | None = None
        value: int | str | None = None
        assert cur_label is not None, "Translation failed: Data declaration or definition can't be done without label, line: {}".format(term.line)
        assert cur_label not in labels, "Translation failed: labels in section data are not unique, line: {}".format(term.line)
        labels.add(cur_label)

        data_terms: list[DataTerm] = []
        str_data_term: DataTerm | None = None

        def validate_string_size(size_str: str) -> int:
            data_size = try_convert_str_to_int(term.terms[2])
            assert data_size is not None and data_size > 0, "Translation failed: data size should be non-negative integer value, line: {}".format(term.line)  # noqa: PT018
            return data_size

        match len(term.terms):
            case 2: # Number declaration
                data_terms.append(DataTerm(index = data_index, label = cur_label,  value = value, size = data_size, line = term.line))
            case 3: # Number defenition
                value = try_convert_str_to_int(term.terms[2])
                assert value is not None, "Translation failed: number defenition is not correct, line:{}".format(term.line)
                assert value < 2**31 and value >= -2**32, "Translation failed: number doesn't fit machine word, which is 4 bytes, line: {}".format(term.line)  # noqa: PT018
                data_terms.append(DataTerm(index = data_index, label = cur_label,  value = value, size = data_size, line = term.line))
            case 4: # String data declaration
                data_size = validate_string_size(term.terms[2])
                str_data_term = DataTerm(index = data_index, label = cur_label, value = value, size = data_size, line = term.line)
                data_terms.extend(map_literal_to_data_terms(str_data_term))
            case 5: # String data defenition
                data_size = validate_string_size(term.terms[2])
                assert try_convert_str_to_int(term.terms[4]) is None, "Translation failed: number shouldn't have length before it, line: {}".format(term.line)
                # String without quotes
                value = term.terms[4][1:-1]
                assert isinstance(value, str)
                assert len(value) == data_size, "Translation failed: given data size doen't match given string."
                str_data_term = DataTerm(index = data_index, label = cur_label, value = value, size = data_size, line = term.line)
                data_terms.extend(map_literal_to_data_terms(str_data_term))
            case _:
                raise AssertionError("Translation failed: data term doen't fit declaration or definition rules, line: {}".format(term.line))
        complete_data_terms.extend(data_terms)
        labels_addr[cur_label] = data_index
        data_index += 1

    logging.debug("Data terms :")
    [logging.debug(term) for term in complete_data_terms]
    logging.debug("==========================")
    logging.debug("Data labels indicies:")
    logging.debug(labels_addr)
    logging.debug("==========================")
    return (complete_data_terms, labels_addr)

def map_sections(interruption_vector: list[StatementTerm | DataTerm], statement_terms: list[StatementTerm],
                    statement_labels_addr: dict[str, int], data_terms: list[DataTerm], data_labels_addr: dict[str, int]
                ) -> tuple[Code, dict[str, int], dict[str, int]]:
    """ Отображение термов программы на память."""
    code: Code = Code()
    programm_start: int | None = None
    for statement_pos, statement in enumerate(statement_terms):
            if statement.label is not None and statement.label == "_start":
                programm_start = statement_pos
                break

    assert programm_start is not None, "Translation failed: can not find programm start label."

    code.contents.extend(interruption_vector)
    code.contents.extend(statement_terms[programm_start:])
    code.contents.extend(statement_terms[:programm_start])
    code.contents.extend(data_terms)

    term_index: int = 0
    for term in code.contents:
        term.index = term_index
        if isinstance(term, StatementTerm) and term.label is not None:
            statement_labels_addr[term.label] = term_index
        elif isinstance(term, DataTerm) and term.label is not None:
            data_labels_addr[term.label] = term_index
        term_index += 1

    print("code maped")
    [print(term) for term in code.contents]
    print("========================")
    return (code, statement_labels_addr, data_labels_addr)

def link_sections(code: Code, statement_labels_addr: dict[str, int], data_labels_addr: dict[str, int]) -> Code:
    """ Линковка секций программы

    Подстановка адресов термов вместо лейблов в аргументах инструкций в соответствии с типом инструкции.
    """
    for term in code.contents:
        if isinstance(term, StatementTerm) and term.arg is not None and isinstance(term.arg, str):
            if term.opcode in Opcode.control_flow_operations():
                term.arg = statement_labels_addr[term.arg]
            elif term.opcode in Opcode.data_manipulation_operations():
                term.arg = data_labels_addr[term.arg]

    print("code linked")
    [print(term) for term in code.contents]
    return code

def create_interruption_vector() -> tuple(list[DataTerm], dict[str, int], dict[str, int]):
    """ Создание вектора прерываний и словаря лейблов и их индексов.

    Вектор прерываний состоит из адресов обработчиков прерываний и инструкция int относится к категории
     инструкций управления выполнения, поэтому состоит из термов данных, хранящих адреса обработчиков.
    По умолчанию, вектор прерываний неинициализирован, поэтому разработчику необходимо инициализировать его вручную,
    сохраняя адреса лейблов в необходимые вектора прерываний при старте программы.

    Возвращает список термов содержащих вектор прерывания и ячейки памяти для регистров, словарь лейблов вектора
     прерываний и словарь лейблов ячеек памяти для регистров.
    """
    interruption_vector: [list[DataTerm]] = []
    interruption_vector_labels: dict[str, int] = dict()
    interruption_register_labels: dict[str, int] = dict()

    for index in range(0, get_interruption_vector_length() + 1):
        if index < get_interruption_vector_length():
            label: str = "int{}".format(index)
            interruption_vector.append(DataTerm(index = index, label = label, value = 0))
            interruption_vector_labels[label] = index
        else:
            interruption_vector.append(DataTerm(index = index, label = "int_acc", value = 0))
            interruption_vector.append(DataTerm(index = index + 1, label = "int_pc", value = 0))
            interruption_register_labels["int_acc"] = index
            interruption_register_labels["int_pc"] = index + 1
    return (interruption_vector, interruption_vector_labels, interruption_register_labels)

def translate(code_text: str) -> Code:
    """ Трансляция текста исходной программы в машинный код для модели процессора.

    В процессе трансляции сохраняются адреса лейблов данных и кода для подстановки адресов.
    """
    code: Code | None = None
    section_data: list[SourceTerm] | None = None
    section_text: list[SourceTerm] | None = None
    code_labels: dict[str, int] = dict()
    data_labels: dict[str, int] = dict()
    interruption_vector: list[StatementTerm | DataTerm] = []
    interruption_vector_labels: dict[str, int] = dict()
    interruption_registers_labels: dict[str, int] = dict()
    statement_terms: list[StatementTerm] = []
    data_terms: list[DataTerm] = []

    source_terms: list[SourceTerm] = split_text_to_source_terms(code_text)
    sections: dict[str, list[SourceTerm]] = split_source_terms_to_sections(source_terms)

    section_data = sections.get(".data")
    if section_data is not None:
        data_terms, data_labels = map_terms_to_data(section_data)

    interruption_vector, interruption_vector_labels, interruption_registers_labels = create_interruption_vector()
    data_labels.update(interruption_registers_labels)
    print(interruption_registers_labels)
    print(interruption_vector_labels)

    section_text = sections.get(".text")
    assert section_text is not None, "Translation failed: Section .text is not present in program"
    statement_terms, code_labels = map_terms_to_statements(section_text, {key for key in data_labels.keys()})
    code_labels.update(interruption_vector_labels)

    code, code_labels, data_labels = map_sections(interruption_vector, statement_terms, code_labels, data_terms, data_labels)
    return link_sections(code, code_labels, data_labels)

logging.debug(Opcode.data_manipulation_operations())
logging.debug("===============")
curdir = os.path.dirname(__file__)
ex_file = os.path.join(curdir, "../examples/hello.asm")
file = open(ex_file)
code = file.read()
translate(code)

def main(source_code_file_name: str, target_file_name: str) -> None:
    """ Функция запуска транслятора.

    Параметры:
    - Файл с исходным кодом программы.
    - Файл, в который в случае успеха трансляции будет записан машинный код.
    """
    with open(source_code_file_name, encoding="utf-8") as f:
        source = f.read()

    code = translate(source)

    write_code(target_file_name, code)
    logging.info("source LoC:", len(source.split("\n")), "code instr:", len(code.contents))

if __name__ == "__main__":
    # logging.basicConfig(
    #     level = logging.DEBUG,
    #     # filemode="w+",
    #     # format="%(asctime)s [%(levelname)s] %(message)s",
    #     handlers=[
    #         logging.FileHandler("logs/translator.log"),
    #         logging.StreamHandler(sys.stdout)
    #     ])
    logging.getLogger().addHandler(logging.FileHandler("logs/translator.log"))
    logging.getLogger().setLevel(logging.DEBUG)

    def excepthook(*args: Any) -> None:
        """ Логирование всех необрабатываемых исключений"""
        logging.getLogger().error("Uncaught exception:", exc_info=args)
    sys.excepthook = excepthook

    logging.info("Translation started...")
    assert len(sys.argv) == 3, "Translation failed: Wrong arguments. Correct way is: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
    logging.info("Transation ended.")

