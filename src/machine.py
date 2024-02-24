from __future__ import annotations

import logging
import sys

from devices import IODevice, SPIController
from isa import Code, DataTerm, Mode, Opcode, StatementTerm, read_code

# Начальное состояние регистра - счётчика команд
MACHINE_START_ADDR: int = 10

INTERRRUPTION_VECTOR_LENGTH: int = 8


def get_machine_start_addr() -> int:
    return MACHINE_START_ADDR


def get_interruption_vector_length() -> int:
    return INTERRRUPTION_VECTOR_LENGTH


def raise_error(err_msg: str = "") -> None:
    raise ValueError("Internal error X_X : " + err_msg)

def bool2int(val: bool) -> int:
    return 1 if val else 0


class DataPath:
    # Регистр - аккумулятор
    _accumulator_register: int

    # AR регистр
    _address_register: int

    # Буфферный регистр для хранения
    _buffer_register: int

    # Флаг, сигнализирующий о знаке результата последнего цикла исполнения команды
    _neg_flag: bool

    # Флаг, сигнализирующий о равенстве нулю результата последнего цикла исполнения команды
    _zero_flag: bool

    # Устройство, хранящее таблицу соответствия номеров устройств - векторам прерывания.
    # _device_interpution_table: list[tuple[int, int]]

    # Общая память, к которой DataPath обращается для чтения/записи данных
    _memory: list[StatementTerm | DataTerm]

    # Арифметико - логическое устройство
    _alu: ALU

    def __init__(
        self, common_memory: list[StatementTerm | DataTerm]
    ) -> None:
        self._accumulator_register = 0
        self._address_register = 0
        self._buffer_register = 0
        self._neg_flag = False
        self._zero_flag = True
        self._memory = common_memory
        self._alu = DataPath.ALU()

    class ALU:
        """Арифметико - логическое устройство

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
            self.reset_registers()
            self._res_zero = True
            self._res_neg = False

        def reset_registers(self) -> None:
            """Загрузка '0' во внутренние регистры"""
            self._left_register = 0
            self._right_register = 0

        def negative(self, mode: int) -> None:
            """Инверсия данных

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
                    raise_error("Incorrect data_path/alu/negative mode")

        def inc(self, mode: int) -> None:
            """Инкремент данных

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
                    self._right_register += 1
                case 2:
                    self._left_register += 1
                    self._right_register += 1
                case 3:
                    pass
                case _:
                    raise_error("Incorrect data_path/alu/zero mode")

        def dec(self, mode: int) -> None:
            """Декремент данных

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
                    self._right_register -= 1
                case 2:
                    self._left_register -= 1
                    self._right_register -= 1
                case 3:
                    pass
                case _:
                    raise_error("Incorrect data_path/alu/dec mode")

        def operation(self, mode: int) -> None:
            """Операция над данными

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
                    self._output_buffer_register = self._left_register // self._right_register
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
                    raise_error("Incorrect data_path/alu/operation mode")
            self._res_neg = self._output_buffer_register < 0
            self._res_zero = self._output_buffer_register == 0

    def update_flags(self) -> None:
        self._zero_flag = self._alu._res_zero
        self._neg_flag = self._alu._res_neg

    def _read_memory(self) -> int:
        """Чтение из памяти по адресу из адресного регистра значения в аккумулятор."""
        assert isinstance(self._memory[self._address_register].value, int)
        return self._memory[self._address_register].value

    def _write_memory(self) -> None:
        """Запись в память по значению адресного регистра значения аккумулятора."""
        self._memory[self._address_register].value = self._accumulator_register

    def zero(self) -> bool:
        """Возврат значения"""
        return self._zero_flag

    def negative(self) -> bool:
        return self._neg_flag


class ControlUnit:
    """Логический модуль машины, отвечающий за управление потоком выполнения машины."""

    _tick: int
    """ Счётчик тактов с начала работы модели машины."""

    _programm_counter_register: int
    """ IP регистр - используется для доступа к памяти при передаче адреса, значение по которому необходимо "достать"."""

    _instruction_register: StatementTerm | None
    """ Регистр инструкций. Хранит в себе текущее выражение на исполенние (инструкцию с аргументом) после цикла выборки команд."""

    _interruption_enabled: bool
    """ Регистр - указывающий возможно ли выполнить прерывание в текущем цикле исполнения инструкции."""

    _interruption_request: bool
    """ Регистр - указывающий есть ли запрос на прерывание от подключённых устройств."""

    _interruption_state: bool
    """ Флаг нахождения машины в состоянии прерывания."""

    _instruction_decoder: InstructionDecoder
    """ Дешифратор инструкций."""

    _memory: list[StatementTerm | DataTerm]
    """ Общая память, из которой модулем управления выбираются команды."""

    _spi_controller: SPIController
    """ Контроллер ввода/вывода интерфейса SPI."""

    _data_path: DataPath
    """ Соединение с DataPath для управления манипулированием данными."""

    def __init__(self, common_memory: list[StatementTerm | DataTerm], data_path: DataPath, spi_controller: SPIController) -> None:
        self._tick = 0
        self._interruption_enabled = False
        self._interruption_request = False
        self._interruption_state = False
        self._programm_counter_register = MACHINE_START_ADDR
        self._instruction_register = None
        self._instruction_decoder = ControlUnit.InstructionDecoder()
        self._memory = common_memory
        self._data_path = data_path
        self._spi_controller = spi_controller

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
        """Увеличение счётчика процессорных тактов."""
        self._tick += 1

    def get_tick(self) -> int:
        return self._tick

    def signal_interrupt(self) -> None:
        pass

        # ???

    def signal_input(self, select: int) -> None:
        """ Сигнал ввода данных в аккумулятор с указанного порта ввода.

        Выбор порта происходит постредством передачи управляющих сигналов на демультиплексор контроллера SPI.
        В реализации процессора доступно 8 устройств ввода/вывода.
        Управляющие сигналы:
        0 - SCLK
        1 - MOSI
        2 - MISO
        3 - CS0
        4 - CS1
        ...
        10 - CS7
        11 - INT0
        12 - INT1
        ...
        17 - INT7
        """
        signal: bool | None = None
        match select:
            case 2:
                signal = self._spi_controller._devices.get(2)._miso
            case 11:
                signal = self._spi_controller._devices.get(11)
            case 1 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10:
                pass
        if signal is not None:
                self._data_path._accumulator_register | signal

    def signal_output(self, select: int) -> None:
        """ Сигнал вывода данных из аккумулятора на указанный порт вывода.

        Выбор порта происходит постредством передачи управляющих сигналов на демультиплексор контроллера SPI.
        В реализации процессора доступно 8 устройств ввода/вывода.
        Управляющие сигналы:
        0 - SCLK
        1 - MOSI
        2 - MISO
        3 - CS0
        4 - CS1
        ...
        10 - CS7
        11 - INT0
        ...
        17 - INT7
        """
        signal: bool = True if self._data_path._accumulator_register & 1 == 1 else False
        match select:
            case 0:
                self._spi_controller.signal_sclk(signal = signal)
            case 1:
                self._spi_controller.signal_mosi(signal = signal)
            case 2:
                pass
            case 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10:
                self._spi_controller.signal_cs(chip_select = select, signal = signal)
            case 11:
                self._spi_controller._interruption_request = signal
            case _:
                raise_error("Incorrect control_unit/signal_spi select")

    def signal_latch_address_register(self, select: int) -> None:
        """Сигнал записи данных в адресный регистр через мультиплексор.

        Происходит посредством установки селектора. Каждый вариант селектора влияет на источник поступаемых данных.
        Селекторы:
        0 - instr_arg (control_unit/instruction_register.arg)
        1 - buf_reg (data_path/buffer_register)
        2 - int_acc (fix address in memory)
        3 - int_pc (fix address in memory)
        """
        match select:
            case 0:
                assert self._instruction_register is not None
                self._data_path._address_register = self._instruction_register.arg
            case 1:
                self._data_path._address_register = self._data_path._buffer_register
            case 2:
                self._data_path._address_register = INTERRRUPTION_VECTOR_LENGTH
            case 3:
                self._data_path._address_register = INTERRRUPTION_VECTOR_LENGTH + 1
            case _:
                raise_error("Incorrect control_unit/signal_address select")

    def signal_latch_accumulator_register(self, select: int) -> None:
        """Сигнал записи данных в аккумуляторный регистр через мультиплексор.

        Происходит посредством установки селектора. Каждый вариант селектора влияет на источник поступаемых данных.
        Селекторы:
        0 - mem (data_path/memory)
        1 - alu (data_path/arithmetical_logical_unit)
        2 - io (data_path/SPI...)
        3 - pc (control_unit/programm_counter_register)
        """
        match select:
            case 0:
                self._data_path._accumulator_register = self._data_path._read_memory()
            case 1:
                self._data_path._accumulator_register = self._data_path._alu._output_buffer_register
            case 2:
                pass  # ...I/O
            case 3:
                self._data_path._accumulator_register = self._programm_counter_register
            case _:
                raise_error("Incorrect control_unit/signal_acc select")

    def signal_latch_buffer_register(self, select: int) -> None:
        """Сигнал записи данных в буфферный регистр через мультиплексор.

        Происходит посредством установки селектора. Каждый вариант селектора влияет на источник поступаемых данных.
        Селекторы:
        0 - instr_arg (control_unit/instruction_register.arg)
        1 - mem (data_path/memory)
        2 - io_int (SPISlaves/_interruption_request demultiplexer)
        """
        match select:
            case 0:
                assert self._instruction_register is not None
                self._data_path._buffer_register = self._instruction_register.arg
            case 1:
                self._data_path._buffer_register = self._data_path._read_memory()
            # Вызывается только в цикле проверки прерываний
            case 2:
                device_index: int
                for index, device in self._spi_controller._devices.items():
                    if device._interruption_request:
                        device_index = index
                self._data_path._buffer_register = device_index
            case _:
                raise_error("Incorrect control_unit/signal_buff select")

    def signal_latch_arithmetical_logical_unit(self, select: list[int] = [1, 3, 3, 3, 6]) -> None:
        """Сигнал передачи данных в арифметико-логическое устройство.

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
                self._data_path._alu._right_register = self._data_path._accumulator_register
            case 2:
                self._data_path._alu._left_register = self._data_path._buffer_register
                self._data_path._alu._right_register = self._data_path._accumulator_register
            case 3:
                pass
            case _:
                raise_error("Incorrect control_unit/signal_alu select")
        self._data_path._alu.negative(select[1])
        self._data_path._alu.inc(select[2])
        self._data_path._alu.dec(select[3])
        self._data_path._alu.operation(select[4])
        self._data_path.update_flags()
        self._data_path._alu.reset_registers()

    def signal_latch_programm_counter_register(self, select: int) -> None:
        """Сигнал записи данных в регистр - счётчик команд через мультиплексор.

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
                raise_error("Incorrect control_unit/signal_pc select")


    def _prepare_for_interruption(self) -> None:
        """ Подготовка машины к обработке прерывания.

        Сохранение аккумулятора и счётчика команд в определенные для этого ячейки памяти,
        установка флага обработки прерывания и сохранение номера прерывания в аккумулятор.
        """
        # Запись в память значения аккумулятора
        self.signal_latch_address_register(select=2)
        self.perform_tick()
        self._data_path._write_memory()
        self.perform_tick()
        # Запись в память значения регистра - счётчика команд
        self.signal_latch_accumulator_register(select=3)
        self.perform_tick()
        self.signal_latch_address_register(select=3)
        self.perform_tick()
        self._data_path._write_memory()
        self.perform_tick()
        # Изменение значения счётчика команд
        self.signal_latch_address_register(select=1)
        self.perform_tick()
        self.signal_latch_buffer_register(select=1)
        self.perform_tick()
        self.signal_latch_programm_counter_register(select=0)
        self.perform_tick()
        self._interruption_state = True
        self.signal_latch_arithmetical_logical_unit(select=[0, 3, 3, 3, 6])
        self.signal_latch_accumulator_register(select=1)
        self.perform_tick()


    def _select_instruction(self) -> None:
        """Цикл выборки инструкции из памяти по адресу счётчика команд.

        Имеет место допущение, что доступ к памяти происходит за такт процессора."""
        self._instruction_register = self._memory[self._programm_counter_register]
        self.perform_tick()
        self.signal_latch_programm_counter_register(select=1)
        self.perform_tick()

    def _decode_instruction(self) -> None:
        assert self._instruction_register is not None
        self._instruction_decoder.signal_latch_opcode(self._instruction_register.opcode)
        self._instruction_decoder.signal_latch_mode(self._instruction_register.mode)
        print("decoder: ", self._instruction_decoder._opcode, self._instruction_decoder._mode)
        self.perform_tick()

    def _select_argumet(self) -> None:
        """Цикл выборки аргумента"""
        match self._instruction_decoder._mode:
            # Непосредственная адресация - запись в буфер аргумента команды
            case Mode.VALUE:
                self.signal_latch_buffer_register(select=0)
                self.perform_tick()
            # Прямая адресация - запись в буфер значения по адресу из аргумента команды
            case Mode.DIRECT:
                self.signal_latch_address_register(select=0)
                self.perform_tick()
                self.signal_latch_buffer_register(select=1)
                self.perform_tick()
            # Косвенная адресация - запись в буфер значения по адресу, располагающемуся по адресу из аргумента команды
            case Mode.INDIRECT:
                self.signal_latch_address_register(select=0)
                self.perform_tick()
                self.signal_latch_buffer_register(select=1)
                self.perform_tick()
                self.signal_latch_address_register(select=1)
                self.perform_tick()
                self.signal_latch_buffer_register(select=1)
                self.perform_tick()
            case None:
                self.perform_tick()
            case _:
                raise ValueError("Mode at some instruction in source code is incorrect.")

    def _execute_instruction(self) -> None:
        match self._instruction_decoder._opcode:
            case Opcode.LD:
                self.signal_latch_arithmetical_logical_unit(select=[0, 3, 3, 3, 6])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.ST:
                self.signal_latch_address_register(select=1)
                self.perform_tick()
                self._data_path._write_memory()
                self.perform_tick()
            case Opcode.IN:
                self.signal_input(select = self._data_path._buffer_register)
                self.perform_tick()
            case Opcode.OUT:
                self.signal_output(select = self._data_path._buffer_register)
                self.perform_tick()
            case Opcode.ADD:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 0])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.SUB:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 1])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.CMP:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 1])
                self.perform_tick()
            case Opcode.INC:
                self.signal_latch_arithmetical_logical_unit(select=[1, 3, 1, 3, 6])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.DEC:
                self.signal_latch_arithmetical_logical_unit(select=[1, 3, 3, 1, 6])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.MUL:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 2])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.DIV:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 3])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.MOD:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 4])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.AND:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 5])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.OR:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 6])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.LSL:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 7])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.ASR:
                self.signal_latch_arithmetical_logical_unit(select=[2, 3, 3, 3, 8])
                self.signal_latch_accumulator_register(select=1)
                self.perform_tick()
            case Opcode.JMP:
                self.signal_latch_programm_counter_register(select=0)
                self.perform_tick()
            case Opcode.JZ:
                if self._data_path.zero():
                    self.perform_tick()
                    self.signal_latch_programm_counter_register(select=0)
                self.perform_tick()
            case Opcode.JNZ:
                if not self._data_path.zero():
                    self.perform_tick()
                    self.signal_latch_programm_counter_register(select=0)
                self.perform_tick()
            case Opcode.JN:
                if self._data_path.negative():
                    self.perform_tick()
                    self.signal_latch_programm_counter_register(select=0)
                self.perform_tick()
            case Opcode.JP:
                if not self._data_path.negative():
                    self.perform_tick()
                    self.signal_latch_programm_counter_register(select=0)
                self.perform_tick()
            case Opcode.INT:
                self._prepare_for_interruption()
            case Opcode.FI:
                # Чтение из памяти значение счётчика команд
                self.signal_latch_address_register(select=3)
                self.perform_tick()
                self.signal_latch_buffer_register(select=1)
                self.perform_tick()
                self.signal_latch_programm_counter_register(select=0)
                self.perform_tick()
                # Чтение из памяти значения аккумулятора
                self.signal_latch_address_register(select=2)
                self.perform_tick()
                self.signal_latch_accumulator_register(select=0)
                self.perform_tick()
                # Обнуление флага обработки прерывания
                self._interruption_state = False
            case Opcode.ENI:
                self._interruption_enabled = True
                self.perform_tick()
            case Opcode.DII:
                self._interruption_enabled = False
                self.perform_tick()
            case Opcode.NOP:
                self.perform_tick()
            case Opcode.HLT:
                raise StopIteration()
            case _:
                raise_error("Unknown opcode in instruction execute cycle")

    def _check_interruption(self) -> None:
        if self._interruption_enabled and self._interruption_request:
            self.signal_latch_buffer_register(select=2)
            self._prepare_for_interruption()

    def execute_next_command(self) -> None:
        """Выполнение циклов исполнения команды."""
        self._select_instruction()
        self._decode_instruction()
        self._select_argumet()
        self._execute_instruction()
        self._check_interruption()


class Machine:
    """Модель вычислительной машины с фон-Неймановской архитектурой.
    Память представлена отдельным модулем, к которому имеют доступ тракт данных и управляющий модуль.
    """

    # Кол-во ячеек памяти машины (в размерах машинного слова - 4 байта)
    _memory_size: int

    # Память машины. Используется трактом данных и управляющим модулем.
    _common_memory: list[StatementTerm | DataTerm]

    # Список "подключённых" устройств ввода/вывода
    _io_devices: dict[int, IODevice]

    # Модель тракта данных в машине.
    _data_path: DataPath

    # Модель управляющего модуля в машине.
    _control_unit: ControlUnit

    # Контроллер ввода/вывода интерфейса SPI.
    _spi_controller: SPIController

    _output_buffer: list[str]

    def __init__(self,
                memory_size: int = 4096,
                io_devices: dict[int, IODevice] = dict()
                ) -> None:
        assert memory_size > 0, "Memory size should not be zero."
        self._memory_size = memory_size
        # Возможность для использования стека, если не задавать размер памяти, равный количеству машинных выражений
        self._common_memory = [DataTerm(index = index) for index in range(0, memory_size)]
        self._io_devices = io_devices
        self._data_path = DataPath(self._common_memory)
        self._spi_controller = SPIController(slaves = self._io_devices)
        self._control_unit = ControlUnit(common_memory = self._common_memory, data_path = self._data_path, spi_controller = self._spi_controller)
        self._output_buffer = []

    def __repr__(self) -> str:
        """Вернуть строковое представление состояния процессора."""
        assert self._control_unit._instruction_register is not None
        return "TICK: {:3} PC: {:3} IR: '{:^11}' IRQ: {} IE: {} IS: {} AC: {:^10} AR: {:3} BR: {:3} N: {}, Z: {}".format(
            self._control_unit.get_tick(),
            self._control_unit._programm_counter_register,
            self._control_unit._instruction_register.opcode,
            bool2int(self._control_unit._interruption_request),
            bool2int(self._control_unit._interruption_enabled),
            bool2int(self._control_unit._interruption_state),
            self._control_unit._data_path._accumulator_register,
            self._control_unit._data_path._address_register,
            self._control_unit._data_path._buffer_register,
            bool2int(self._control_unit._data_path.negative()),
            bool2int(self._control_unit._data_path.zero())
        )


    @staticmethod
    def parse_schedule(list_tuple_text: str) -> list[tuple[int, str]]:
        """Парсинг расписания ввода символов по тактам из текста с соответствующими данными."""
        # мб убрать кавычки
        list_schedule: list[tuple[int, str]] = list(eval(list_tuple_text)) if list_tuple_text.strip() != "" else []
        return list_schedule

    def simulation(
        self, code: Code, input_schedule: list[tuple[int, str]] = [], limit: int = 1000
    ) -> tuple[str, int, int]:
        """Подготовка модели и запуск симуляции процессора.

        Возвращает вывод программы, значение счётчика команд и кол-во исполненных тактов.
        """
        assert limit > 0, "Simulation failed: Limit can not be negative or zero."
        self._common_memory[:len(code.contents)] = code.contents
        cur_schedule: int | None = 0 if len(input_schedule) > 0 else None
        try:
            while self._control_unit.get_tick() < limit:
                # Логика управлением расписания вводом/выводом
                if cur_schedule is not None and self._control_unit.get_tick() >= input_schedule[cur_schedule][0]:
                    self._spi_controller._devices[3]._shift_register = input_schedule[cur_schedule][1]
                    self._spi_controller._devices[3]._interruption_request = True

                self._control_unit.execute_next_command()
                # Сбор данных с устройств вывода
                if self._spi_controller._devices[4]._transfer_finished:
                    self._output_buffer.append(chr(self._spi_controller._devices[4]._shift_register))
                    self._spi_controller._devices[4]._transfer_finished = False
                logging.info(self.__repr__())
        except StopIteration:
            logging.info(self.__repr__())

        if self._control_unit.get_tick() >= limit:
            logging.warning("Instruction limit exceeded!")
        logging.info("Output_buffer:\n" + repr("".join(self._output_buffer)))
        return ("".join(self._output_buffer),
                self._control_unit._programm_counter_register,
                self._control_unit.get_tick())


def main(code: Code, input_file_name: str) -> None:
    """Функция запуска модели процессора. Параметры -- имена файлов с машинным
    кодом и с входными данными для симуляции ввода (формат [<такт подачи символа>, <символ>]).
    """
    machine: Machine

    try:
        code = read_code(code_file)
    except ValueError:
        # use logging.exception to see the stacktrace
        logging.error("Binary instructions can not be loaded properly.")
        return

    [print(inst) for inst in code.contents]

    try:
        with open(input_file_name, encoding="utf-8") as file:
            input_text: str = file.read()
            input_schedule: list[tuple[int, str]] = Machine.parse_schedule(input_text)
            logging.info("Schedule: {}".format(input_schedule))
    except FileNotFoundError as e:
        logging.error(e)
        return

    machine = Machine(
        memory_size = len(code.contents),
        io_devices = {index: IODevice() for index in [0, 1, 2, 3, 4, 5, 6]}
        )

    try:
        output, instr_counter, ticks = machine.simulation(
            code = code,
            input_schedule = input_schedule,
        )
    except ValueError as e:
        # use logging.exception to see the stacktrace
        logging.error("Error: Instruction parameters are incorrect or instruction decoder doesn't know how to handle some instructions.")
        logging.error("Watch latest instruction in logs.")
        logging.error(e.args[0])
        return
    except TypeError as e:
        # use logging.exception to see the stacktrace
        logging.error("Internal error")
        logging.exception(e.args[0])
        return

    print("".join(output))
    logging.info("instr_counter: {} ticks: {}".format(machine._control_unit._programm_counter_register, machine._control_unit.get_tick()))


if __name__ == "__main__":
    # logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(logging.FileHandler("logs/machine.log"))
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    logging.info("====================\nExecution started...")
    main(code_file, input_file)
    logging.info("Execution ended.")
