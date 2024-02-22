from __future__ import annotations

import logging
import sys

# from devices import IODevice, SPIController
from isa import Code, DataTerm, Mode, Opcode, StatementTerm, read_code

# Начальное состояние регистра - счётчика команд
MACHINE_START_ADDR: int = 10

INTERRRUPTION_VECTOR_LENGTH: int = 8

def get_machine_start_addr() -> int:
    return MACHINE_START_ADDR

def get_interruption_vector_length() -> int:
    return INTERRRUPTION_VECTOR_LENGTH

def raise_error() -> None:
    raise ValueError("Internal error ◑﹏◐")

class DataPath:

    # Регистр - аккумулятор
    _accumulator_reg: int

    # AR регистр
    _address_register: int

     # Буфферный регистр для хранения
    _buffer_register: int

    # Флаг, сигнализирующий о знаке результата последнего цикла исполнения команды
    _neg_flag: bool

    # Флаг, сигнализирующий о равенстве нулю результата последнего цикла исполнения команды
    _zero_flag: bool

    # Устройство, хранящее таблицу соответствия номеров устройств - векторам прерывания.
    _device_interpution_table: list[tuple[int, int]]

    # Общая память, к которой DataPath обращается для чтения/записи данных
    _memory: list[StatementTerm | DataTerm]

    # Арифметико - логическое устройство
    _alu: ALU

    # Буффер выходных данных
    _output_buffer: list[str]

    def __init__(self, common_memory: list[StatementTerm | DataTerm], interruption_table: list[tuple[int, int]]) -> None:
        self._accumulator_reg = 0
        self._address_register = 0
        self._buffer_register = 0
        self._neg_flag = False
        self._zero_flag = True
        self._device_interpution_table = interruption_table
        self._memory = common_memory
        self._alu = ALU()

    class ALU:
        """ Арифметико - логическое устройство

        Выполняет операции над данными из аккумулятора и буферного регистров согласно поданым сигналам.
        Левый вход присоединён к буфферному регистру, правый - к аккумуляторному.
        Содержит внутренние регистры для проведения операций над данными.
        """
        _output_buffer_register: int
        _left_register: int
        _right_register: int
        _res_zero: bool
        _res_neg: bool

        def __init__(self) -> None:
            self._output_buffer_register = 0
            self._left_register = 0
            self._right_register = 0
            self._res_zero = True
            self._res_neg = False

        def reset_registers(self) -> None:
            """ Загрузка '0' во внутренние регистры"""
            self._left_register = 0
            self._right_register = 0


        def negative(self, mode: int) -> None:
            """ Инверсия данных

            Опции:
            0 - только левый вход
            1 - только правый вход
            2 - оба
            3 - ни один
            """
            match mode:
                case 0:
                    self._left_register = ~self._left_register + 1
                case 1:
                    self._right_register = ~self._right_register + 1
                case 2:
                    self._left_register = ~self._left_register + 1
                    self._right_register = ~self._right_register + 1
                case 3:
                    pass
                case _:
                    raise_error()

        def inc(self, mode: int) -> None:
            """ Инкремент данных

            Опции:
            0 - только левый вход
            1 - только правый вход
            2 - оба
            3 - ни один
            """
            match mode:
                case 0:
                    self._left_register += 1
                case 1:
                    self._right_register +=  1
                case 2:
                    self._left_register += 1
                    self._right_register += 1
                case 3:
                    pass
                case _:
                    raise_error()

        def dec(self, mode: int) -> None:
            """ Декремент данных

            Опции:
            0 - только левый вход
            1 - только правый вход
            2 - оба
            3 - ни один
            """
            match mode:
                case 0:
                    self._left_register -= 1
                case 1:
                    self._right_register -=  1
                case 2:
                    self._left_register -= 1
                    self._right_register -= 1
                case 3:
                    pass
                case _:
                    raise_error()

        def operation(self, mode: int) -> None:
            """ Операция над данными

            Опции:
            0 - сложение
            1 - вычитание
            2 - умножение
            3 - деление
            4 - остаток от деления
            5 - логическое "И"
            6 - логическое "ИЛИ"
            7 - логический побитовый сдвиг влево
            8 - арифметический побитовый сдвиг вправо
            """
            match mode:
                case 0:
                    self._output_buffer_register = self._left_register + self._right_register
                case 1:
                    self._output_buffer_register = self._left_register - self._right_register
                case 2:
                    self._output_buffer_register = self._left_register * self._right_register
                case 3:
                    self._output_buffer_register = self._left_register / self._right_register
                case 4:
                    self._output_buffer_register = self._left_register % self._right_register
                case 5:
                    self._output_buffer_register = self._left_register & self._right_register
                case 6:
                    self._output_buffer_register = self._left_register | self._right_register
                case 7:
                    self._output_buffer_register = self._left_register << self._right_register
                case 8:
                    self._output_buffer_register = self._left_register >> self._right_register
                case _:
                    raise_error()
            self._res_neg = self._output_buffer_register < 0
            self._res_zero = self._output_buffer_register == 0

    def update_flags(self) -> None:
        self._zero_flag = self._alu._res_zero
        self._neg_flag = self._alu._res_neg

    def _read_memory(self) -> int:
        return self._memory[self._address_register]

    def _write_memory(self) -> None:
        self._memory[self._address_register] = self._accumulator_reg

    def zero(self) -> bool:
        return self._zero_flag

    def negative(self) -> bool:
        return self._neg_flag


class ControlUnit:
    # Счётчик тактов с начала работы модели машины
    _tick: int

    # IP регистр - используется для доступа к памяти при передаче адреса, значение по которому необходимо "достать"
    _programm_counter_register: int

    # Регистр инструкций. Хранит в себе текущее выражение на исполенние (инструкцию с аргументом) после цикла выборки команд
    _instruction_register: StatementTerm | None


    # Регистр - указывающий возможно ли выполнить прерывание в текущем цикле исполнения инструкции.
    _interruption_enabled: bool

    # Модуль дешифрации команд
    _instruction_decoder: InstructionDecoder

    # Общая память, из которой выбираются команды
    _memory: list[StatementTerm | DataTerm]

    _data_path: DataPath

    def __init__(self, common_memory: list[StatementTerm | DataTerm], data_path: DataPath) -> None:
        self._tick = 0
        self._interruption_enabled = False
        self._programm_counter_register = MACHINE_START_ADDR
        self._instruction_register = None
        self._instruction_decoder = InstructionDecoder()
        self._memory = common_memory
        self._data_path = data_path

    class InstructionDecoder:
        _step_counter: int

        _opcode: Opcode | None

        _mode: Mode | None

        def __init__(self) -> None:
            self._step_counter = 0
            self._opcode = None
            self._mode = None

        def signal_latch_opcode(self, opcode: Opcode) -> None:
            self._opcode = opcode

        def signal_latch_mode(self, mode: Mode) -> None:
            self._mode = mode


    def perform_tick(self) -> None:
        """ Увеличение счётчика процессорных тактов. """
        self._tick += 1

    def get_tick(self) -> int:
        return self._tick

    def signal_interrupt(self) -> None:
        pass

    def signal_output(self) -> None:
        output_symbol = chr(self._accumulator_reg)
        logging.info("Output: %s + %s", repr("".join(self.output_buffer)), repr(output_symbol))
        self._output_buffer.append[output_symbol]

    def signal_latch_address_register(self, select: int) -> None:
        """ Сигнал записи данных в адресный регистр через мультиплексор.

        Происходит посредством установки селектора. Каждый вариант селектора влияет на источник поступаемых данных.
        Селекторы:
        0 - instr_arg (control_unit/instruction_register.arg)
        1 - buf_reg (data_path/buffer_register)
        2 - ...
        """
        match select:
            case 0:
                self._data_path._address_register = self._instruction_register.arg
            case 1:
                self._data_path._address_register = self._data_path._buffer_register
            case _:
                raise_error()

    def signal_latch_accumulator_register(self, select: int) -> None:
        """ Сигнал записи данных в аккумуляторный регистр через мультиплексор.

        Происходит посредством установки селектора. Каждый вариант селектора влияет на источник поступаемых данных.
        Селекторы:
        0 - mem (data_path/memory)
        1 - alu (data_path/arithmetical_logical_unit)
        2 - io (data_path/SPI...)
        """
        match select:
            case 0:
                self._data_path._accumulator_reg = self._data_path._read_memory()
            case 1:
                self._data_path._accumulator_reg = self._data_path._alu._output_buffer_register
            case 2:
                pass ...
            case _:
                raise_error()

    def signal_latch_buffer_register(self, select: int) -> None:
        """ Сигнал записи данных в буфферный регистр через мультиплексор.

        Происходит посредством установки селектора. Каждый вариант селектора влияет на источник поступаемых данных.
        Селекторы:
        0 - instr_arg (control_unit/instruction_register.arg)
        1 - mem (data_path/memory)
        2 - ...
        """
        match select:
            case 0:
                self._data_path._buffer_register = self._instruction_register.arg
            case 1:
                self._data_path._buffer_register = self._data_path._read_memory()
            case _:
                raise_error()

    def signal_latch_arithmetical_logical_unit(self, select: list[int] = [1, 3, 3, 3, 6]) -> None:
        """ Сигнал передачи данных в арифметико-логическое устройство.

        Происходит посредством установки селекторов. Представлена списком опций.
        Каждая позиция в списке селектора влияет на способ обработки данных АЛУ.

        Опции селекторов по позициям:
        0: зашелкивание данных в АЛУ
            0 - использовать только буфферынй регистр (левый)
            1 - использовать только аккумуляторный регистр (правый)
            2 - использовать данные с обоих регистров
        1: инверсия данных
            0 - только левый вход
            1 - только правый вход
            2 - оба
            3 - ни один
        2: инкремент данных
            0 - только левый вход
            1 - только правый вход
            2 - оба
            3 - ни один
        3: декремент данных
            0 - только левый вход
            1 - только правый вход
            2 - оба
            3 - ни один
        4: операция над данными
            0 - сложение
            1 - вычитание
            2 - умножение
            3 - деление
            4 - остаток от деления
            5 - логическое "И"
            6 - логическое "ИЛИ"
            7 - логический побитовый сдвиг влево
            8 - арифметический побитовый сдвиг вправо
        """
        match select[0]:
            case 0:
                self._data_path._alu._left_register = self._data_path._buffer_register
            case 1:
                self._data_path._alu._right_register = self._data_path._accumulator_reg
            case 2:
                self._data_path._alu._left_register = self._data_path._buffer_register
                self._data_path._alu._right_register = self._data_path._accumulator_reg
            case 3:
                pass
            case _:
                raise_error()
        self._data_path._alu.negative(select[1])
        self._data_path._alu.inc(select[2])
        self._data_path._alu.dec(select[3])
        self._data_path._alu.operation(select[4])
        self._data_path._alu.reset_registers()

    def signal_latch_programm_counter_register(self, select: int) -> None:
        """ Сигнал записи данных в регистр - счётчик команд через мультиплексор.

        Происходит посредством установки селектора. Каждый вариант селектора влияет на источник поступаемых данных.
        Селекторы:
        0 - buf_reg (data_path/buffer_register)
        1 - pc_inc (control_unit/programm_counter_register + 1)
        """
        match select:
            case 0:
                self._programm_counter_register = self._data_path._buffer_register
                self.perform_tick()
            case 1:
                self._programm_counter_register += 1
            case _:
                raise_error()


    def _select_instruction(self) -> None:
        """ Цикл выборки инструкции из памяти по адресу счётчика команд.

        Имеет место быть допущение, что доступ к памяти происходит за такт процессора."""
        self._instruction_register = self._memory[self._programm_counter_register]
        self.perform_tick()

    def _decode_instruction(self) -> None:
        self._instruction_decoder.signal_latch_opcode(self._instruction_register.opcode)
        self._instruction_decoder.signal_latch_mode(self._instruction_register.mode)
        self.perform_tick()

    def _select_argumet(self) -> None:
        """ Цикл выборки аргумента"""
        match self._instruction_decoder._mode:
            # Непосредственная адресация - запись в буфер аргумента команды
            case Mode.VALUE:
                self.signal_latch_buffer_register(select = 0)
                self.perform_tick()
            # Прямая адресация - запись в буфер значения по адресу из аргумента команды
            case Mode.DIRECT:
                self.signal_latch_address_register(select = 0)
                self.perform_tick()
                self.signal_latch_buffer_register(select = 1)
                self.perform_tick()
            # Косвенная адресация - запись в буфер значения по адресу, располагающемуся по адресу из аргумента команды
            case Mode.INDIRECT:
                self.signal_latch_address_register(select = 0)
                self.perform_tick()
                self.signal_latch_buffer_register(select = 1)
                self.perform_tick()
                self.signal_latch_address_register(select = 1)
                self.perform_tick()
                self.signal_latch_buffer_register(select = 1)
                self.perform_tick()
            case None:
                self.perform_tick()
            case _:
                raise ValueError("Mode at instruction on line {} in source code is incorrect.".format(self._instruction_register.line))

    def _execute_instruction(self) -> None:
        match self._instruction_decoder._opcode:
            case Opcode.LD:
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.ST:
                self.signal_latch_address_register(select = 1)
                self.perform_tick()
                self._data_path._write_memory()
                self.perform_tick()
            case Opcode.ADD:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 0])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.SUB:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 1])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.CMP:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 1])
                self.perform_tick()
            case Opcode.MUL:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 2])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.DIV:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 3])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.MOD:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 4])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.AND:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 5])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.OR:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 6])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.LSL:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 7])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.ASR:
                self.signal_latch_arithmetical_logical_unit(select = [2, 3, 3, 3, 8])
                self.signal_latch_accumulator_register(select = 1)
                self.perform_tick()
            case Opcode.JMP:
                self.signal_latch_programm_counter_register(select = 0)
                self.perform_tick()
            case Opcode.JZ:
                if self._data_path._zero_flag:
                    self.perform_tick()
                    self.signal_latch_programm_counter_register(select = 0)
                self.perform_tick()
            case Opcode.JNZ:
                if not self._data_path._zero_flag:
                    self.perform_tick()
                    self.signal_latch_programm_counter_register(select = 0)
                self.perform_tick()
            case Opcode.JN:
                if self._data_path._neg_flag:
                    self.perform_tick()
                    self.signal_latch_programm_counter_register(select = 0)
                self.perform_tick()
            case Opcode.JP:
                if not self._data_path._neg_flag:
                    self.perform_tick()
                    self.signal_latch_programm_counter_register(select = 0)
                self.perform_tick()
            case _:
                raise_error()

    def _check_interrution(self) -> None:
        pass

    def execute_next_command(self) -> None:
        """ Выполнение циклов исполнения команды."""
        self._select_instruction()
        self._decode_instruction()
        self._select_argumet()
        self._execute_command()
        self._check_interruption()
        # self.signal_latch_programm_counter_register(select = 1)


class Machine:
    """ Модель вычислительной машины с фон-Неймановской архитектурой.
    Память представлена отдельным модулем, к которому имеют доступ тракт данных и управляющий модуль.
    """

    # Кол-во ячеек памяти машины (в размерах машинного слова - 4 байта)
    memory_size: int

    # Память машины. Используется трактом данных и управляющим модулем.
    common_memory: list[StatementTerm | DataTerm]

    # Список "подключённых" устройств ввода/вывода
    # io_devices: list[IODevice] = []

    # Модель тракта данных в машине.
    _data_path: DataPath

    # Модель управляющего модуля в машине.
    _control_unit: ControlUnit

    # Буфер для хранения расписания ввода символов
    _input_buffer: list[tuple[int, str]]

    def __init__(self, memory_size: int = 4096, input_buffer: list[tuple[int, str]] = [], limit: int = 1000):
        assert memory_size > 0, "Memory size should not be zero."
        assert limit > 0, "Limit can not be negative or zero."
        self.memory_size = memory_size
        self.common_memory = [0] * memory_size
        self.data_path = DataPath(self.common_memory)
        self.control_unit = ControlUnit(self.common_memory)
        self._input_buffer = input_buffer


    def __repr__(self) -> str:
        """Вернуть строковое представление состояния процессора."""
        return "TICK: {:3} PC: {:3} ADDR: {:3} MEM_OUT: {} ACC: {}".format(
            self._tick,
            self.program_counter,
            self.data_path.data_address,
            self.data_path.data_memory[self.data_path.data_address],
            self.data_path.acc,
        )

    @staticmethod
    def parse_schedule(self, list_tuple_text: str) -> list[tuple[int, str]]:
        """ Парсинг расписания ввода символов по тактам из текста с соответствующими данными.
        """
        list_schedule: list[tuple[int, str]] = []
        for t in list_tuple_text:
            a, b = t.strip("()").split(",")
            list_schedule.append((int(a), int(b)))
        return list_schedule


    def simulation(self, code: Code, input_schedule: list[tuple[int, str]], limit: int) -> tuple[output: str, instr_counter: int, ticks: int]:
        """Подготовка модели и запуск симуляции процессора.

        Возвращает вывод программы, значение счётчика команд и кол-во исполненных тактов.
        """
        try:
            while self._control_unit.get_tick() < self.limit:
                self._control_unit.execute_next_command()

                

        except ValueError:
            logging.error("Instruction parameters are incorrect.")
        except StopIteration:
            pass


def main(code: Code, input_file_name: str) -> None:
    """Функция запуска модели процессора. Параметры -- имена файлов с машинным
    кодом и с входными данными для симуляции ввода (формат [<такт подачи символа>, <символ>]).
    """
    machine: Machine


    code = read_code(code_file)
    with open(input_file_name, encoding="utf-8") as file:
        input_text: str = file.read()
        input_schedule: list[tuple[int, str]] = Machine.parse_schedule(input_text)

    machine = Machine(memory_size = code.contents[-1].index, limit = 1000)

    output, instr_counter, ticks = machine.simulation(
        code = code,
        input_schedule = input_schedule,
    )
    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)

if __name__ == "__main__":
    # logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.FileHandler("logs/machine.log"))
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
