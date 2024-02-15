from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from json import JSONEncoder
from typing import Any


class Code:
    """ Представление структуры для хранения машинного кода"""
    # Контейнер для хранения машинных инструкций.
    contents: list[StatementTerm | DataTerm]

    def __init__(self, contents: list[StatementTerm | DataTerm] = []) -> None:
        self.contents = []

    def __str__(self) -> str:
        return self.contents.__str__()

    def append(self, elem: StatementTerm | DataTerm) -> None:
        self.contents.append(elem)

    @staticmethod
    def to_json(code: Code) -> str:
        return CodeEncoder().encode(code.contents)

class CodeEncoder(JSONEncoder):
    """ Вспомогательный класс для получения строкового представления машинного кода. """
    def default(self, obj: Code) -> dict[str, Any]:
        return obj.__dict__

class Opcode(str, Enum):
    """ Opcode инструкций языка.

    Могут быть поделёны на две группы:

    1. Операции управления выполнением: "JMP", "JZ", "JNZ", "JN",
     "JNN", "HLT", "INT", "ENI", "DII".

    2. Операции над данными: все остальные


    и на две категории:

    1. Исполняемые без аргументов: "INC", "DEC", "ENI", "DII", "HLT", "NOP".

    2. Исполняемые с одним аргументом: все остальные.
    """

    LD = "load"
    ST = "store"
    OUT = "output"
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
    NOP = "no operation"

    @staticmethod
    def data_manipulation_operations() -> set[Opcode]:
        """ Множество манипулирующих данными команд с одним аргументом

        Аргументами этих команд являются индексы данных(адреса), значения или лейблы данных.
        """
        return {Opcode.LD, Opcode.ST, Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV,
                 Opcode.CMP, Opcode.OR, Opcode.AND, Opcode.OUT, Opcode.IN}

    @staticmethod
    def control_flow_operations() -> set[Opcode]:
        """ Множество управляющих потоком управления команд с одним аргументом

        Аргументами этих команд являются лейблы инструкций.
        """
        return {Opcode.JMP, Opcode.JZ, Opcode.JNZ, Opcode.JN, Opcode.JNN, Opcode.INT}

    @staticmethod
    def unary_operations() -> set[Opcode]:
        """ Множество команд с одним аргументом

        Аргументами этих команд являются индексы, значения или лейблы инструкций / данных.
        """
        return Opcode.data_manipulation_operations().union(Opcode.control_flow_operations())

    @staticmethod
    def no_operand_operations() -> set[Opcode]:
        """ Множество команд без аргументов"""
        return {Opcode.HLT, Opcode.ENI, Opcode.DII, Opcode.INC, Opcode.DEC, Opcode.NOP}

    def __str__(self) -> str:
        """Переопределение стандартного поведения `__str__` для `Enum`: вместо
        `Opcode.JZ` вернуть `jump zero`.
        """
        return str(self.value)

    def __repr__(self) -> str:
        return self.__str__()

class Mode(str, Enum):
    """ Указание режима интерпретации аргумента. """
    DEREF = "deref"
    """ Аргумент - адрес, по которому находится необходимое значение """
    VALUE = "value"
    """ Аргумет - непосредственно значение """

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return self.__str__()

class StatementTerm:
    """ Структура для описания команды с аргументом из кода программы."""
    index: int
    label: str | None
    opcode: Opcode | None
    arg: int | None | str
    mode: Mode | None
    # Source code reference
    line: int

    def __init__(self, index: int, label: str | None, opcode: Opcode | None,
                 arg: int | None, mode: Mode | None, line: int) -> None:
        self.index = index
        self.label = label
        self.opcode = opcode
        self.arg = arg
        self.mode = mode
        self.line = line

    @staticmethod
    def from_json(json_obj: Any) -> StatementTerm | None:
        try:
            json_obj["opcode"] = Opcode(json_obj["opcode"])
            json_obj["mode"] = Mode(json_obj["mode"])
            instance: StatementTerm = StatementTerm(**json_obj)
        except (TypeError, KeyError):
            return None
        return instance

    def __str__(self) -> str:
        return {key: value for key, value in self.__dict__.items() if value is not None}.__str__()

    def __repr__(self) -> str:
        return self.__str__()


class DataTerm:
    """ Структура для представления данных в памяти. """
    index: int
    label: str | None
    value: int | str | None
    size: int | None
    line: int

    def __init__(self, index: int, label: str, value: int | str | None,
                 size: int, line: int) -> None:
        self.index = index
        self.label = label
        self.value = value
        self.size = size
        self.line = line

    @staticmethod
    def from_json(json_obj: Any) -> DataTerm | None:
        try:
            instance: DataTerm = DataTerm(**json_obj)
        except (TypeError, KeyError):
            return None
        return instance

    def __str__(self) -> str:
        return {key: value for key, value in self.__dict__.items() if value is not None}.__str__()

    def __repr__(self) -> str:
        return self.__str__()

class SourceTerm:
    """ Структура для представления строки исходного кода. """
    line: int
    terms: list[str]

    def __init__(self, line_num: int, line_split: list[str]) -> None:
        self.line = line_num
        self.terms = line_split

    def __str__(self) -> str:
        return "line: {}, terms: {}\n".format(self.line, self.terms)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SourceTerm):
            return self.line == other.line and self.terms == other.terms
        return False

def read_code(filename: str) -> Code:
    """ Чтение машинного кода из файла. """

    with open(filename, encoding="utf-8") as file:
        code_text: list[dict[str, Any]] = json.loads(file.read())
        code: Code = Code()

    for instr in code_text:
        # Конвертация json объекта в экземпляр StatementTerm
        term: StatementTerm | DataTerm | None = StatementTerm.from_json(instr)
        if term is None:
            # В случае неудачи, конвертация в экземпляр DataTerm
            term = DataTerm.from_json(instr)

        assert term is not None

        code.append(term)

    return code


def write_code(filename: str, code: Code) -> None:
    """Записать машинный код в файл. """
    with open(filename, "w", encoding="utf-8") as file:
        buf = Code.to_json(code)
        file.write(buf)
