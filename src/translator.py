from __future__ import annotations

import logging
import os
import re
import sys

from isa import Code, DataTerm, Mode, Opcode, SourceTerm, StatementTerm, write_code


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
    try:
        statement.terms.index("*")
        mode = Mode.DEREF
    except ValueError:
        mode = Mode.VALUE
    return mode

def validate_unary_operation_argument(statement: SourceTerm, opcode: Opcode, operation_labels: set[str], data_labels: set[str]) -> int | str:
        """ Проверка аргументов инструкций с одним аргументом."""
        arg_term: str | None = statement.terms[1] if len(statement.terms) >= 2 else None
        assert arg_term is not None, "Translation failed: invalid unary opration argument, line: {}".format(statement.line)
        arg: int | str | None = None
        is_control_flow_operation: bool = opcode in Opcode.control_flow_operations()
        is_data_manipulation_operation: bool = opcode in Opcode.data_manipulation_operations()
        assert is_control_flow_operation ^ is_data_manipulation_operation, "Translation bug: ISA represents opcode '{}' incorrectly, line: {}".format(opcode, statement.line)
        if is_control_flow_operation:
            assert arg_term in operation_labels, "Translation failed: control flow instruction argument should be an operation statement label, line: {}".format(statement.line)
            arg = arg_term
        elif is_data_manipulation_operation:
            assert arg_term not in operation_labels, "Translation failed: statement label provided to data manipulation instruction, line: {}".format(statement.line)
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
    cur_label: str | None = match_label(statement)
    # Убираем имя лейбла из выражения при наличии
    if cur_label is not None:
        del statement.terms[:2]

    mode: Mode | None = None
    mode = select_remove_statement_mode(statement)
    # Убираем символ косвенной адресации
    if mode == Mode.DEREF is not None:
        statement.terms.remove("*")

    opcode: Opcode | None = None
    arg: str | int | None = None
    instruction_name: str | None = statement.terms[0] if len(statement.terms) > 0 else None
    if instruction_name is not None:
        opcode = map_instruction_to_opcode(instruction_name) if instruction_name is not None else None
        assert opcode is not None, "Translation failed: instruction {} is not supported, line: {}".format(instruction_name, statement.line)
        is_unary_operation: bool = opcode in Opcode.unary_operations()
        is_noop_operation: bool = opcode in Opcode.no_operand_operations()
        assert is_unary_operation ^ is_noop_operation, "Translation bug: ISA represents opcode '{}' incorrectly, line: {}".format(opcode, statement.line)
        if is_unary_operation:
            arg = validate_unary_operation_argument(statement, opcode, operation_labels, data_labels)
        elif is_noop_operation:
            assert is_noop_operation and len(statement.terms) == 1, "Translation failed: instruction {} works without arguments, line: {}".format(opcode, statement.line)  # noqa: PT018
            mode = None
    return StatementTerm(index = instruction_counter, label = cur_label, opcode = opcode, arg = arg, mode = mode, line = statement.line)

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

def map_text_to_data(data_section_terms: list[SourceTerm]) -> tuple[list[DataTerm], dict[str, int]]:
    """ Трансляция последовательности термов секции данных исходной программы в последовательность термов данных.

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
        assert cur_label is not None, "Translation failed: Data declaration or definition can't be done without label, line: {}".format(term.line)
        assert cur_label not in labels, "Translation failed: labels in section data are not unique, line: {}".format(term.line)
        labels.add(cur_label)

        def validate_string_size(size_str: str) -> int:
            data_size = try_convert_str_to_int(term.terms[2])
            assert data_size is not None and data_size > 0, "Translation failed: data size should be non-negative integer value, line: {}".format(term.line)  # noqa: PT018
            return data_size

        match len(term.terms):
            case 2: # Number declaration
                data_size = 4
            case 3: # Number defenition
                data_size = 4
                value = try_convert_str_to_int(term.terms[2])
                assert value is not None, "Translation failed: number defenition is not correct, line:{}".format(term.line)
                assert value < 2**31 and value >= -2**32, "Translation failed: number doesn't fit machine word, which is 4 bytes, line: {}".format(term.line)  # noqa: PT018
            case 4: # String data declaration
                data_size = validate_string_size(term.terms[2])
            case 5: # String data defenition
                data_size = validate_string_size(term.terms[2])
                assert try_convert_str_to_int(term.terms[4]) is None, "Translation failed: number shouldn't have length before it, line: {}".format(term.line)
                # String without quotes
                value = term.terms[4][1:-1]
                assert isinstance(value, str)
                assert len(value) == data_size, "Translation failed: given data size doen't match given string."
            case _:
                raise AssertionError("Translation failed: data term doen't fit declaration or definition rules, line: {}".format(term.line))

        data_term: DataTerm = DataTerm(index = instruction_counter, label = cur_label,  value = value, size = data_size, line = term.line)
        data_terms.append(data_term)
        labels_addr[cur_label] = instruction_counter
        instruction_counter += data_size

    logging.debug("Data terms :")
    [logging.debug(term) for term in data_terms]
    logging.debug("==========================")
    logging.debug("Data labels indicies:")
    logging.debug(labels_addr)
    logging.debug("==========================")
    return (data_terms, labels_addr)

def link_sections(statement_terms: list[StatementTerm], statement_labels_addr: dict[str, int], data_terms: list[DataTerm], data_labels_addr: dict[str, int]) -> Code:
    data_section_end_addr: int = data_terms[-1].index + data_terms[-1].size

    programm_start: int | None = None
    for statement in statement_terms:
        if statement.label is not None and statement.label == "_start":
            programm_start = statement.index
            # либо перемещать части программы, чтобы старт была на 0 позиции в памяти
            # либо создавать логику загрузки PC в машину (сложно)

    arg = (labels_addr[arg_terms[0]] if arg_terms[0] in data_labels else try_convert_str_to_int(arg_terms[0]) )
    assert arg is not None, "Translation failed: incorrect data manipulation instruction argument, line: {}".format(statement.line)
    

def translate(code_text: str) -> Code:
    """ Трансляция текста исходной программы в машинный код для модели процессора.

    В процессе трансляции сохраняются адреса лейблов данных и кода для подстановки адресов.
    """
    code: Code | None = None
    section_data: list[SourceTerm] | None = None
    section_text: list[SourceTerm] | None = None
    code_labels: dict[str, int] = dict()
    data_labels: dict[str, int] = dict()
    statement_terms: list[StatementTerm] = []
    data_terms: list[DataTerm] = []

    source_terms: list[SourceTerm] = split_text_to_source_terms(code_text)
    sections: dict[str, list[SourceTerm]] = split_source_terms_to_sections(source_terms)

    section_data = sections.get(".data")
    if section_data is not None:
        data_terms, data_labels = map_text_to_data(section_data)

    section_text = sections.get(".text")
    assert section_text is not None, "Translation failed: Section .text is not present in program"
    statement_terms, code_labels = map_terms_to_statements(section_text, {key for key in data_labels.keys()})

    code = link_sections(statement_terms, code_labels, data_terms, data_labels)


    for adress, statement in enumerate(statement_terms, 1):
        pass

    return code

logging.debug(Opcode.data_manipulation_operations())
logging.debug("===============")
curdir = os.path.dirname(__file__)
ex_file = os.path.join(curdir, "../examples/hello.asm")
file = open(ex_file)
code = file.read()
translate(code)
# terms = []
# # logging.debug(code)
# terms = split_text_to_source_terms(code)
# # logging.debug(terms)
# logging.debug("====================")
# sections: dict[str, list[SourceTerm]] = split_source_terms_to_sections(terms)
# logging.debug(sections)

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
    logging.info("source LoC:", len(source.split("\n")), "code instr:", len(code.contents))

if __name__ == "__main__":
    # logging.basicConfig(
    #     level = logging.DEBUG,
    #     format="%(asctime)s [%(levelname)s] %(message)s",
    #     handlers=[
    #         # logging.FileHandler(os.path.join(os.path.dirname(__file__), "../log/translator.log")),
    #         logging.StreamHandler(sys.stdout)
    #     ])
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info("Translation started...")
    assert len(sys.argv) == 3, "Translation failed: Wrong arguments. Correct way is: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
    logging.info("Transation ended.")

