from __future__ import annotations

import sys

from isa import Code, DataTerm, Opcode, StatementTerm, write_code


def avaliable_sections() -> dict[str, str]:
    return {"data": "section .data", "bss": "section .bss", "intv": "section .intv", "text": "section .text"}

def get_section_name(name: str) -> str:
    return avaliable_sections().get(name)


def symbols() -> set[str]:
    """ Полное множество символов, доступных к использованию в языке.

    Используется для парсинга секций данных и определения способа адресации лейблов.
    """
    return {":", "*", ",", ";", """, """}


def instructions() -> set[str]:
    """ Полное множество команд, доступных к использованию в языке. """
    return [opcode.name.lower() for opcode in Opcode]

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

def split_text_to_sections(programm_text: str) -> dict[str, str]:
    """ Разделение исходного кода программы по секциям для отдельной обработки.

    Возвращаемые значения:
    - текст секции .data
    - текст секции .bss
    - текст секции .intv
    - текст секции .text
    """
    sections: dict[str, str] = {}
    sections_starts: dict[str, int] = {}

    # Находим и сохраняем начало каждой секции
    sections_starts.update({"data": programm_text.find(get_section_name("data"))})
    sections_starts.update({"bss": programm_text.find(get_section_name("bss"))})
    sections_starts.update({"intv": programm_text.find(get_section_name("intv"))})
    sections_starts.update({"text": programm_text.find(get_section_name("text"))})

    # Сортируем секции по их порядку нахождения в файле
    sections_starts = {key: value for key, value in sorted(sections_starts.items(), key=lambda item: item[1])}

    # Добавляем каждой секции в выходной структуре её содержимое без заголовка секции
    prev_pair: tuple[str, int] = None
    for name, position in sections_starts.items():
        if prev_pair is not None or position != -1:
            start: int = prev_pair[1] if prev_pair[1] != -1 else 0
            indent: int = start + len(get_section_name(prev_pair[0])) + 1
            sections.update({ prev_pair[0]: programm_text[indent : position].strip() })
        prev_pair = (name, position)
    start: int = prev_pair[1] if prev_pair[1] != -1 else 0
    indent: int = start + len(get_section_name(prev_pair[0])) + 1
    sections.update({ prev_pair[0]: programm_text[indent : ].strip() })

    print("data", sections["data"])
    print("bss", sections["bss"])
    print("intv", sections["intv"])
    print("text", sections["text"])
    print("+++++++++++++++++++====")

    return sections

def match_label():
    pass

def filter_comments_on_line(terms: list[str]) -> list[str]:
    comment_start: int = None
    for term_num, term in terms:
        if term == ";":
            comment_start = term_num
    if comment_start is not None:
        terms = terms[:comment_start]
    return terms

li = list["a", ";", "gegeg", "sffe"]
li2 = list[";", "efffe", "afwef"]
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

def map_text_to_row_data(row_data_section_text: str) -> list[DataTerm]:
    """ Трансляция секции инициализированных данных в термы памяти для выделения им места в машинном коде.
    """
    line_num: int
    line: str
    labels: set[str] = set()
    terms: set[DataTerm] = set()
    for line_num, line in enumerate(row_data_section_text.split("\n"), 1):
        assert len(line.split()) == 2, "Failed to translate: statements have too many arguments. section data -> line: {}".format(line_num)
        elements: tuple[str, int] = line.split()
        assert elements[0] not in labels, "Failed to translate: labels in section .bss are not unique. section data -> line: {}".format(line_num)
        assert isinstance(elements[1], int), "Failed to translate: length should be int value. section data -> line: {}".format(line_num)
        labels.add(elements[0])
        term: DataTerm = DataTerm(line = line_num, label = elements[0], length = elements[1])
        terms.add(term)


def map_text_to_predef_data(predef_data_section_text: str) -> list[DataTerm]:
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

def translate(code_text: str) -> Code:
    """ Трансляция текста исходной программы в машинный код для процессора.

    В процессе трансляции сохраняются адреса лейблов данных и кода для подстановки адресов.
    """
    code: Code = Code()
    section_data: str
    section_bss: str
    section_intv: str
    section_text: str
    code_labels: dict[str, int]
    data_labels: dict[str, int]
    code_terms: list[StatementTerm] = []
    data_terms: list[DataTerm] = []

    sections = split_text_to_sections(code_text)

    section_intv = sections.get("intv")
    interruption_terms = map_text_to_terms(section_intv)

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

