from __future__ import annotations

import logging
import sys

from isa import Opcode, read_code


class DataPath:
    # AC регистр
    accumulator_reg: int

    # AR регистр
    adress_reg:int

    # Устройство, хранящее таблицу соответствия номеров устройств - векторам прерывания.
    device_interpution_table: list[tuple[int, int]]



    # Буффер выходных данных
    output_buffer: list[str]

    def __init__(self, interruption_table: list[tuple[int, int]]):
        accumulator_reg = 0
        adress_reg = 0
        device_interpution_table = interruption_table

    def signal_output(self) -> None:
        output_symbol = chr(self.accumulator_reg)
        logging.debug("Output: %s + %s", repr("".join(self.output_buffer)), repr(output_symbol))
        self.output_buffer.append[output_symbol]

    def zero(self) -> bool:
        return self.accumulator_reg == 0

    def negative(self) -> bool:
        return self.accumulator_reg < 0



class ControlUnit:
    # Счётчик тактов с начала работы модели машины
    _tick: int

    # IP регистр - используется для доступа к памяти при передаче адреса, значение по которому необходимо "достать"
    instruction_pointer_reg: int

    # Регистр - указывающий возможно ли выполнить прерывание в текущем цикле исполнения инструкции.
    interruption_enabled: bool

    def __init__(self, limit: int):
        interruption_enabled = False


    def tick(self) -> None:
        pass


    def perform_next_tick(self) -> None:
        """ Выполнение следующего процессорного такта. """
        pass

    def signal_interrupt(self) -> None:
        pass

    def __repr__(self) -> str:
        """ Вернуть состояние процессора в строковом представлении.
        """

        return 


class Machine:
    """ Модель вычислительной машины с фон-Неймановской архитектурой.
    Память представлена отдельным модулем, к которому имеют доступ тракт данных и управляющий модуль.
    """

    # Кол-во ячеек памяти машины (в размерах машинного слова - 4 байта)
    memory_size: int

    # Память машины. Используется трактом данных и управляющим модулем.
    common_memory: list[int]

    # Модель тракта данных в машине.
    _data_path: DataPath

    # Модель управляющего модуля в машине.
    _control_unit: ControlUnit

    # Буфер для хранения расписания ввода символов
    _input_buffer: list[tuple[int, str]]

    def __init__(self, memory_size: int, input_buffer: list[tuple[int, str]], limit: int):
        assert memory_size > 0, "Memory size should not be zero"
        assert limit > 0, "Limit can not be negative"
        self.memory_size = memory_size
        self.common_memory = [0] * memory_size
        self.data_path = DataPath(self.common_memory)
        self.control_unit = ControlUnit(common_memory, limit)
        self._input_buffer = input_buffer


    def __repr__(self) -> str:
        """Вернуть строковое представление состояния процессора."""
        state_repr = "TICK: {:3} PC: {:3} ADDR: {:3} MEM_OUT: {} ACC: {}".format(
            self._tick,
            self.program_counter,
            self.data_path.data_address,
            self.data_path.data_memory[self.data_path.data_address],
            self.data_path.acc,
        )
        return state_repr

    def decode_instruction_select_argument(self) -> None:
        pass

    def check_interrution(self) -> None:
        pass

    def execute_next_command(self) -> None:
        self.decode_instruction_select_argument()
        self.execute_command()
        self.check_interruption()


    def simulation(self, code: Code, input_schedule: list[tuple[int, str]], data_memory_size: int, limit: int) -> tuple[output: str, instr_counter: int, ticks: int]:
        """Подготовка модели и запуск симуляции процессора.
        Возвращает вывод программы, значение счётчика команд и кол-во исполненных тактов.
        """

    def parse_schedule(self, list_tuple_text: str) -> list[tuple[int, str]]:
        """ Парсинг расписания ввода символов по тактам из текста с соответствующими данными.
        """
        list_schedule = []
        for t in list_tuple_text:
            a, b = t.strip("()").split(",")
            tuples.append((int(a), int(b)))
        return list_schedule

def main(code: Code, input_file_name: str) -> None:
    """Функция запуска модели процессора. Параметры -- имена файлов с машинным
    кодом и с входными данными для симуляции ввода (формат [<такт подачи символа>, <символ>]).
    """
    machine: Machine

    code = read_code(code_file)
    with open(input_file_name, encoding="utf-8") as file:
        input_text: str = file.read()
        input_schedule: list[tuple[int, str]] = parse_schedule(input_text)

    machine = Machine(memory_size, )

    output, instr_counter, ticks = simulation(
        code,
        input_schedule=input_schedule,
        data_memory_size=100,
        limit=1000,
    )
    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
