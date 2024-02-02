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

    def __init__(self) -> None:
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

    def __str__(self) -> str:
        """Переопределение стандартного поведения `__str__` для `Enum`: вместо
        `Opcode.JZ` вернуть `jump zero`.
        """
        return str(self.value)

class Mode(str, Enum):
    """ Аргумент - адрес, по которому нужно взять значение """
    DEREF = "deref"
    """ Аргумет - значение, используемое напрямую """
    VALUE = "value"

    def __str__(self) -> str:
        return str(self.name)


@dataclass(frozen = True)
class StatementTerm:
    """ Структура для описания команды с аргументом из кода программы.

    Frozen служит для объявления объектов класса иммутабельными для автоматической генерации хэша
    """
    index: int
    opcode: Opcode
    arg: int
    mode: Mode
    # Source code reference
    line: int

    @staticmethod
    def from_json(json_obj: Any) -> StatementTerm | None:
        try:
            json_obj["opcode"] = Opcode(json_obj["opcode"])
            json_obj["mode"] = Mode(json_obj["mode"])
            instance: StatementTerm = StatementTerm(**json_obj)
        except (TypeError, KeyError):
            return None
        return instance


@dataclass(frozen = True)
class DataTerm:
    """ Структура для представления значения и длины лейбла в памяти. """
    index: int
    label: str
    value: int | str | None
    line: int

    @staticmethod
    def from_json(json_obj: Any) -> DataTerm | None:
        try:
            instance: DataTerm = DataTerm(**json_obj)
        except (TypeError, KeyError):
            return None
        return instance
    
    def __str__(self) -> str:
        return "{ index: {}, label: }"

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
