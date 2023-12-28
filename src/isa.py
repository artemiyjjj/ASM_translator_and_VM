from __future__ import annotations

import json
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum


class Code:
    """ Представление структуры для хранения машинного кода"""
    # Контейнер для хранения машинных инструкций.
    contents: list[dict[str, int]] = None

    def __init__(self):
        self.contents = []

    def append(self, elem: dict[str, int]):
        self.contents.append(elem)


class Opcode(str, Enum):
    """ Opcode инструкций языка.

    Могут быть поделёны на две группы:

    1. Операции управления выполнением: "JMP", "JZ", "JNZ", "JN",
     "JNN", "HLT", "INT", "ENI", "DII".

    2. Операции над данными: все остальные


    и на две категории:

    1. Исполняемые без аргументов: "INC", "DEC", "ENI", "DII", "HLT".

    2. Исполняемые с одним аргументом: все остальные.
    """

    LD = "load"
    ST = "store"
    OUT = "print"
    IN = "input"
    ADD = "add"
    SUB = "substract"
    CMP = "compare"
    INC = "increment"
    DEC = "decrement"
    MUL = "multiply"
    DIV = "divide"
    OR = "or"
    AND = "and"
    JMP = "jump"
    JZ = "jump zero"
    JNZ = "jump not zero"
    JN = "jump neg"
    JNN = "jump not neg"
    INT = "interruption"
    ENI = "enable interruption"
    DII = "disable interruption"
    HLT = "halt"

    def __str__(self):
        """Переопределение стандартного поведения `__str__` для `Enum`: вместо
        `Opcode.JZ` вернуть `jump zero`.
        """
        return str(self.value)

@dataclass(frozen = True)
class StatementTerm:
    """ Структура для описания команды с аргументом из кода программы.

    Frozen служит для объявления объектов класса иммутабельными для автоматической генерации хэша
    """
    line: int = None
    command: str = None
    argument: int | str = None

@dataclass(frozen = True)
class PositionTerm:
    """ Описание выражения из исходного текста программы. """
    line: int = None
    instruction: str = None

# @dataclass
# class RowDataTerm:
#     """ Структура для представления неициализированных данных в памяти для программы
#     """
#     line: int = None
#     label: str = None
#     length: int = None

@dataclass(frozen = True)
class DataTerm:
    """ Структура для представления значения и длины лейбла в памяти. """
    line: int = None
    label: str = None
    length: int = None
    value: int | str = None


def read_code(filename: str) -> list[dict[str, int]]:
    """ Чтение машинного кода из файла. """
    with open(filename, encoding="utf-8") as file:
        code = json.loads(file.read())

    for instr in code:
        # Конвертация строки в значение Opcode
        instr["opcode"] = Opcode(instr["opcode"])

        # Конвертация списка выражений в класс StatementTerm
        if "term" in instr:
            assert len(instr["term"]) == 2
            instr["term"] = StatementTerm(instr["term"][0], instr["term"][1], instr["term"][2])

    return code


def write_code(filename: str, code: Code) -> None:
    """Записать машинный код в файл. """
    with open(filename, "w", encoding="utf-8") as file:
        buf = []
        for instr in code.contents:
            buf.append(json.dumps(instr))
        file.write("[" + ",\n ".join(buf) + "]")
