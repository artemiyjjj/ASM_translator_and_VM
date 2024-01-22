from __future__ import annotations

import os
import re
import sys
from typing import Optional

from isa import Code, DataTerm, Opcode, SourceTerm, StatementTerm, write_code


def avaliable_sections() -> dict[str, str]:
    return {"data": "section .data", "text": "section .text"}

def get_section_name(name: str) -> str:
    return avaliable_sections()[name]


def symbols() -> set[str]:
    """ Полное множество символов, доступных к использованию в языке.

    Используется для парсинга секций данных и определения способа адресации лейблов.
    """
    return {":", "*", ",", ";", """, """}


def instructions() -> set[str]:
    """ Полное множество команд, доступных к использованию в языке. """
    return {opcode.name.lower() for opcode in Opcode}

def map_instruction_to_opcode(instruction: str) -> Opcode:
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

def split_by_spec_symbols(elem: str) -> list[str]:
        tmp: list[str] = re.split(r"(\:|\;|\,|\*)+", elem)
        while "" in tmp:
            tmp.remove("")
        return tmp

def join_string_literals(terms: list[str]) -> list[str]:
    stack_quotes: list[str] = []
    tmp: list[str] = []
    common: list[str] = []
    indices: list[int] = []
    for term_num, term in enumerate(terms):
        if '"' in term or "'" in term: # упрощенная обработка разных кавычек
            stack_quotes.append("'")
            tmp.append(term)
            indices.append(term_num)
        else:
            common.append(term)
    if len(stack_quotes) > 0:
        print("ind", indices)
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
    term_line: SourceTerm
    for line_num, line in enumerate(programm_text.split("\n")):
        term_line = split_programm_line_to_terms(line)
        if len(term_line) == 0:
            continue
        source_terms.append(SourceTerm(line_num, term_line))
    return source_terms

def split_source_terms_to_sections(programm_text_split: list[SourceTerm]) -> dict[str, list[SourceTerm]]:
    """ Разделение исходного кода программы по секциям для отдельной обработки.

    Возвращаемые значения в словаре:
    - сокращенное имя секции .data и термы строк
    - сокращенное имя секции .text и термы строк
    """
    sections: dict[str, list[SourceTerm]] = dict()
    sections_starts: dict[str, int] = dict()

    # Находим все секции.
    found_sections: list[str] = []
    section_expressions: list[SourceTerm] = [term for term in programm_text_split if "section" in term.terms]
    print("BBB", section_expressions)
    assert len(section_expressions) > 0, "No sections in programm."
    for elem in section_expressions:
        assert elem[0] == ".", "Section name should be prefixed by dot."
        assert elem[2] == ":", "Section name should be followed by colon."
        found_sections.append(elem[1])
    # print(found_expressions)
    # print("found sections", found_sections)

    # Cохраняем начало доступных секций.
    unique_avaliable_sections: set[str] = set()
    for section in found_sections:
        assert section in avaliable_sections().keys(), "Unavaliable section name: {}.".format(section)
        assert section not in unique_avaliable_sections, "Section name should be unique: {}.".format(section)
        section_start: int = programm_text.find(get_section_name(section))
        sections_starts.update({section: section_start})

    # Сортируем секции по их порядку нахождения в файле
    sections_starts = {key: value for key, value in sorted(sections_starts.items(), key=lambda item: item[1])}

    # print(sections_starts)


    # Добавляем каждой секции в выходной структуре её содержимое без заголовка секции
    prev_pair: tuple[str, int] | None = None
    start: int
    indent: int
    for name, position in sections_starts.items():
        if prev_pair is not None:
            start = prev_pair[1]
            indent = start + len(get_section_name(prev_pair[0])) + 1
            sections.update({ prev_pair[0]: programm_text[indent : position].strip() })
        prev_pair = (name, position)
    assert prev_pair is not None
    start = prev_pair[1]
    indent = start + len(get_section_name(prev_pair[0])) + 1
    sections.update({ prev_pair[0]: programm_text[indent : ].strip() })

    # print("data", sections["data"])
    # print("text", sections["text"])
    # print("+++++++++++++++++++====")

    return sections

# def match_label() -> :
#     pass

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

curdir = os.path.dirname(__file__)
ex_file = os.path.join(curdir, "../examples/hello.asm")
file = open(ex_file)
code = file.read()
terms = []
# print(code)
terms = split_text_to_source_terms(code)
for term in terms:
    print(term.terms)
print("====================")
print(split_source_terms_to_sections(terms))


li = ["a", ";", "gegeg", "sffe"]
li2 = [";", "efffe", "afwef"]
li3 = [""]
print(filter_comments_on_line(li))
print(filter_comments_on_line(li2))


def map_text_to_terms(command_section_text: str) -> list[StatementTerm]:
    """ Трансляция тескта секции инструкций исходной программы в последовательность операторов языка.

    Фильтруются незначимые символы, в т. ч. комментарии, проверяется корректность аргументов и уникальность лейблов.
    """
    labels: set[str] = []
    terms: list[Opcode] = []
    for line_num, line in enumerate(command_section_text.split("\n"), 1):
        # print(line_num, line)
        for term_num, term in enumerate(line.split(" "), 1):
            # print("tab   ", term_num, term)
            pass

    return terms

def map_text_to_data(predef_data_section_text: str) -> list[DataTerm]:
    """
    """
    line_num: int
    line: str
    labels: set[str] = set()
    terms: set[DataTerm] = set()
    for line_num, line in enumerate(predef_data_section_text.split("\n"), 1):
        elements: tuple[str, int | str, ...] = line.split()
        assert elements[0] not in labels, "Failed to translate: labels in section .bss are not unique. section data -> line: {}".format(line_num)
        # if 
        assert isinstance(elements[1], int), "Failed to translate: length should be int value. section data -> line: {}".format(line_num)
        labels.add(elements[0])
        term: DataTerm = DataTerm(line = line_num, label = elements[0], length = elements[1])
        terms.add(term)
    return 

def translate(code_text: str) -> Code:
    """ Трансляция текста исходной программы в машинный код для процессора.

    В процессе трансляции сохраняются адреса лейблов данных и кода для подстановки адресов.
    """
    code: Code = Code()
    section_data: str
    section_text: str
    code_labels: dict[str, int]
    data_labels: dict[str, int]
    code_terms: list[StatementTerm] = []
    data_terms: list[DataTerm] = []

    sections = split_text_to_sections(code_text)

    section_text = sections.get("text")
    assert section_text is not None, "Failed to translate: Section .text is not present in program"
    code_terms = map_text_to_terms(section_text)

    section_data = sections.get("data")
    # data_terms.append(map_text_to_predef_data(section_data))

    section_bss = sections.get("bss")
    data_terms.append(map_text_to_row_data(section_bss))

    
    # print(section_bss)
          

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

