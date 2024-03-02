from __future__ import annotations

import logging
import sys

from isa import Code, MachineWordData, MachineWordInstruction, Mode, Opcode, read_code


class DataBus:
    _machine: Machine

    _connected_devices: dict[int, IO.IODeviceCommon]

    transmitting_value: int

    def __init__(self, connected_devices: dict[int, IO.IODeviceCommon] = dict()) -> None:
        self._connected_devices = connected_devices
        self.transmitting_value = 0
        for device in self._connected_devices.values():
            if device._data_bus is None:
                device._data_bus = self

    def connect_device(self, new_device: IO.IODeviceCommon) -> None:
        new_device_index: int = max(list(self._connected_devices.keys())) + 1 if self._connected_devices else 1
        self._connected_devices[new_device_index] = new_device

class InterruptionLine:
    _machine: Machine
    _connected_devices: dict[int, IO.IODeviceCommon]

    def __init__(self, machine: Machine, connected_devices: dict[int, IO.IODeviceCommon] = dict()) -> None:
        self._machine = machine
        self._connected_devices = connected_devices
        for device in self._connected_devices.values():
            if device._int_line is None:
                device._int_line = self

    def connect_device(self, new_device: IO.IODeviceCommon) -> None:
        new_device_index: int = max(list(self._connected_devices.keys())) + 1 if self._connected_devices else 1
        self._connected_devices[new_device_index] = new_device

    def signal_interruption_request(self) -> None:
        self._machine._control_unit.signal_interruption()


# Начальное состояние регистра - счётчика команд
MACHINE_START_ADDR: int = 11

INTERRRUPTION_VECTOR_LENGTH: int = 8


def get_machine_start_addr() -> int:
    return MACHINE_START_ADDR


def get_interruption_vector_length() -> int:
    return INTERRRUPTION_VECTOR_LENGTH


def raise_error(err_msg: str = "") -> None:
    raise ValueError("Internal error X_X : " + err_msg)

def bool2int(val: bool) -> int:
    return 1 if val else 0


class IO:
    class IOController:
        """ Контроллер ввода/вывода для машины.

        Содержит в себе демультиплексор для посылания необходимых управляющих сигналов оперделённым устройствам.
        """
        _connected_devices: dict[int, IO.IODeviceCommon]


        def __init__(self, connected_devices: dict[int, IO.IODeviceCommon]) -> None:
            self._connected_devices = connected_devices

        def send_signal(self, port_addr: int, mode: int) -> None:
            """ Отправление управляющего сигнала на порт устройства.

            Порт определяется исходя из значения аргумента, переданного из буфферного регистра.
            Порты нумеруются с "0", представляя собой последовательность чисел, которыми можно представить все
            регистры всех доступных к подключению устройств ввода/вывода (в данной конфигурации машины - 7 устройств,
            соответственно 14 портов ввода/вывода).

            Каждому порту соответсвуют управляющие сигналы read_int или read_data, wreite_data, которые определяются
            вторым аргументом - mode.

            В случае, если передана комбинация, подразумевающая запись в регистр int какого-либо устрйоства
            - ничего не произойдет.

            Значения port_addr:
            - 0, 1 - устройство 1, регистры int и data соответственно
            - 2, 3 - устройство 2, регистры int и data соответственно
            ...
            - 12, 13 - устройство консольного ввода, регистры int и data соответственно

            Значения mode:
            - 0 - input (device/read)
            - 1 - output (device/write)
            """
            assert port_addr < (get_interruption_vector_length() - 1) * 2, "IO port is out of bounds"
            # В устройствах по 2 регистра, поэтому логика может поменяться при их увеличении
            # однако при увеличении числа устрйоств будет работоспособной
            device_index = (port_addr // 2) + 1
            assert self._connected_devices.get(device_index) is not None, "IO addressed not connected device {}, port {}".format(device_index, port_addr) # debug
            if self._connected_devices.get(device_index) is None:
                return
            if port_addr % 2 == 0:
                if mode == 0:
                    return
                self._connected_devices[device_index].signal_read_int()
            else:
                if mode == 0:
                    self._connected_devices[device_index].signal_read_data()
                else:
                    self._connected_devices[device_index].signal_write_data()


    class IODeviceCommon:
        """ Устройство ввода/вывода

        Для обмена данными с машиной, должно быть "подключено" к её шине данных и линии прерываний(в конструкторе шины и линии).

        Обмен данных происходит за счёт передачи с машины на устройство через контроллер ввода/вывода управляющих сигналов, которые
        позволяют утройству определить, что от него требуется. Логика обработки сигналов представлена
        схемой (см. README/io_).

        """

        _data_bus: DataBus | None

        _int_line: InterruptionLine | None

        _data_register: int
        """ 8-битный регистр для хранения передаваемых/получаемых данных."""

        _int_register: bool
        """ Регистр запроса прерывания.

        Сигнализирует машине о необходимости провести прерывание для считывания данных.
        """

        _new_data: bool
        """ Флаг обновления данных в устройстве."""

        def __init__(self, data_bus: DataBus | None = None, int_line: InterruptionLine | None = None) -> None:
            self._data_bus = data_bus
            self._int_line = int_line
            self._data_register = 0
            self._int_register = False
            self._new_data = False

        def __repr__(self) -> str:
            return "DATA: {:^3} | INT: {} | NEW: {}".format(
                self._data_register,
                self._int_register,
                self._new_data
            )

        def signal_write_data(self) -> None:
            assert self._data_bus is not None
            self._new_data = True
            self._data_register = self._data_bus.transmitting_value

        def signal_read_data(self) -> None:
            assert self._data_bus is not None
            self._data_bus.transmitting_value = self._data_register

        def signal_read_int(self) -> None:
            assert self._data_bus is not None
            self._data_register = ord(self._int_register)
            self._data_bus.transmitting_value = self._data_register

        def signal_int_request(self) -> None:
            assert self._int_line is not None
            self._int_register = True
            self._int_line.signal_interruption_request()

    class IODeviceConsole(IODeviceCommon):
        _input_buffer: list[str] | None = None

        def signal_read_data(self) -> None:
            assert self._data_bus is not None
            if self._input_buffer is None:
                print()
                self._input_buffer = [*input()]
                self._input_buffer.append("\n")
            self._data_register = ord(self._input_buffer[0])
            self._data_bus.transmitting_value = self._data_register
            if len(self._input_buffer) > 1:
                self._input_buffer = self._input_buffer[1:]
            elif len(self._input_buffer) == 1:
                self._input_buffer.append(chr(10)) # EOL symbol
            else:
                self._input_buffer = None


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

    # Общая память, к которой DataPath обращается для чтения/записи данных
    _memory: list[MachineWordInstruction | MachineWordData]

    # Арифметико - логическое устройство
    _alu: ALU

    _data_bus: DataBus

    def __init__(
        self, common_memory: list[MachineWordInstruction | MachineWordData], data_bus: DataBus
    ) -> None:
        self._accumulator_register = 0
        self._address_register = 0
        self._buffer_register = 0
        self._neg_flag = False
        self._zero_flag = True
        self._memory = common_memory
        self._alu = DataPath.ALU()
        self._data_bus = data_bus

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
                    self._output_buffer_register = self._right_register << 1
                case 8:
                    self._output_buffer_register = self._right_register >> 1
                case _:
                    raise_error("Incorrect data_path/alu/operation mode")
            self._res_neg = self._output_buffer_register < 0
            self._res_zero = self._output_buffer_register == 0

    def update_flags(self) -> None:
        self._zero_flag = self._alu._res_zero
        self._neg_flag = self._alu._res_neg

    def _read_memory(self) -> int:
        """Чтение из памяти по адресу из адресного регистра значения в аккумулятор."""
        assert len(self._memory) >= self._address_register, "Access memory out of limited bounds, requested address: {}.".format(self._address_register)
        assert isinstance(self._memory[self._address_register].value, int), "Mem bounds or get value from MemWordInstr"
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

    _instruction_register: MachineWordInstruction | None
    """ Регистр инструкций. Хранит в себе текущее выражение на исполенние (инструкцию с аргументом) после цикла выборки команд."""

    _interruption_enabled: bool
    """ Регистр - указывающий возможно ли выполнить прерывание в текущем цикле исполнения инструкции."""

    _interruption_request: bool
    """ Регистр - указывающий есть ли запрос на прерывание от подключённых устройств."""

    _interruption_state: bool
    """ Флаг нахождения машины в состоянии прерывания."""

    _instruction_decoder: InstructionDecoder
    """ Дешифратор инструкций."""

    _memory: list[MachineWordInstruction | MachineWordData]
    """ Общая память, из которой модулем управления выбираются команды."""

    _data_path: DataPath
    """ Соединение с DataPath для управления манипулированием данными."""

    def __init__(self,
                common_memory: list[MachineWordInstruction | MachineWordData],
                data_path: DataPath,
                io_controller: IO.IOController
            ) -> None:
        self._tick = 0
        self._interruption_enabled = False
        self._interruption_request = False
        self._interruption_state = False
        self._programm_counter_register = MACHINE_START_ADDR
        self._instruction_register = None
        self._instruction_decoder = ControlUnit.InstructionDecoder()
        self._memory = common_memory
        self._data_path = data_path
        self._io_controler = io_controller

    def __repr__(self) -> str:
        """Вернуть строковое представление состояния процессора."""
        assert self._instruction_register is not None
        return "TICK: {:3} | PC: {:3} | IR: '{:^11}' | IRQ: {} | IE: {} | IS: {} | AC: {:^10} | BR: {:3} | AR: {:3} | MEM_AR: {} | N: {} | Z: {}".format(
            self.get_tick(),
            self._programm_counter_register,
            self._instruction_register.opcode,
            bool2int(self._interruption_request),
            bool2int(self._interruption_enabled),
            bool2int(self._interruption_state),
            self._data_path._accumulator_register,
            self._data_path._buffer_register,
            self._data_path._address_register,
            self._data_path._read_memory(),
            bool2int(self._data_path.negative()),
            bool2int(self._data_path.zero())
        )

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
        # logging.debug(self.__repr__())

    def get_tick(self) -> int:
        return self._tick

    def signal_interruption(self) -> None:
        if self._interruption_enabled:
            self._interruption_request = True

    def signal_input_output(self, select_port: int, select_mode: int) -> None:
        """ Сигнал ввода данных из указанного порта вывода на аккумулятор.

        Выбор порта происходит постредством передачи управляющих сигналов на демультиплексор контроллера ввода/вывода.
        В конфигурации процессора доступно 7 устройств ввода/вывода, причём седьмое по умолчанию устройство пользовательского ввода с консоли.

        В случае, если выбран порт, к которому не подключено устройство, ничего не происходит.
        При выборе определенных комбинаций, таких как запись в регистр int любого устройства, также ничего не произойдет.

        Порты:
        - 0, 1 - устройство 1, регистры int и data соответственно
        - 2, 3 - устройство 2, регистры int и data соответственно
        ...
        - 12, 13 - устройство консольного ввода, регистры int и data соответственно

        Параметр mode отвечает за тип передачи:
        0 - ввод,
        1 - вывод
        """
        assert select_port < (get_interruption_vector_length() - 1) * 2, "Incorrect control_unit/signal_spi select"
        self._io_controler.send_signal(port_addr = select_port, mode = select_mode)

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
        2 - io (data_bus)
        3 - pc (control_unit/programm_counter_register)
        """
        match select:
            case 0:
                self._data_path._accumulator_register = self._data_path._read_memory()
            case 1:
                self._data_path._accumulator_register = self._data_path._alu._output_buffer_register
            case 2:
                self._data_path._accumulator_register = self._data_path._data_bus.transmitting_value
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
        2 - io_int (int0 interruption vector)
        """
        match select:
            case 0:
                assert self._instruction_register is not None
                self._data_path._buffer_register = self._instruction_register.arg
            case 1:
                self._data_path._buffer_register = self._data_path._read_memory()
            case 2:
                self._data_path._buffer_register = 0
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
        self.signal_latch_address_register(select=1) # номер обработчика в буффере
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
                self.signal_input_output(select_port = self._data_path._buffer_register, select_mode=0)
                self.signal_latch_accumulator_register(select=2)
                self.perform_tick()
            case Opcode.OUT:
                self._data_path._data_bus.transmitting_value = self._data_path._accumulator_register
                self.signal_input_output(select_port = self._data_path._buffer_register, select_mode = 1)
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
        if self._interruption_request:
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

    _memory_size: int
    """ Кол-во ячеек памяти машины (в размерах машинного слова - 4 байта)."""

    _common_memory: list[MachineWordData | MachineWordInstruction]
    """ Память машины. Используется трактом данных и управляющим модулем."""

    _data_path: DataPath
    """ Модель тракта данных в машине."""

    _control_unit: ControlUnit
    """ """

    _data_bus: DataBus
    """ Шина данных"""

    _int_line: InterruptionLine
    """ Линия прерываний"""

    _io_controller: IO.IOController
    """ Контроллер ввода/вывода."""

    _output_buffer: list[str]
    """ Буффер выходных данных для пользователя"""

    def __init__(self,
                memory_size: int = 4096,
                io_devices: dict[int, IO.IODeviceCommon] = {7: IO.IODeviceConsole()}
                ) -> None:
        assert memory_size > 0, "Memory size should not be zero."
        self._memory_size = memory_size
        # Возможность для использования стека, если задавать размер памяти больший,чем количество машинных выражений
        self._common_memory = [
            MachineWordData(
                index = index,
                label = index,
                value = 0,
                line = 0)
            for index in range(0, memory_size)
        ]
        self._data_bus = DataBus(io_devices)
        self._int_line = InterruptionLine(self, io_devices)
        self._io_controller = IO.IOController(io_devices)
        self._data_path = DataPath(self._common_memory, self._data_bus)
        self._control_unit = ControlUnit(common_memory = self._common_memory, data_path = self._data_path, io_controller = self._io_controller)
        self._output_buffer = []

    def __repr__(self) -> str:
        """Вернуть строковое представление состояния процессора."""
        assert self._control_unit._instruction_register is not None
        device_state: str = ""
        if self._control_unit._instruction_register.opcode in [Opcode.IN, Opcode.OUT]:
            io_port: int = self._control_unit._instruction_register.arg
            device_index: int = io_port // 2 + 1
            device_state = "\n\t Dev: {} | Port: {} | ".format(device_index, io_port) + self._io_controller._connected_devices.get(device_index).__repr__()
        return "TICK: {:3} | PC: {:3} | IR: '{:^11}' | IRQ: {} | IE: {} | IS: {} | AC: {:^10} | BR: {:3} | AR: {:3} | MEM_AR: {} | N: {} | Z: {}".format(
            self._control_unit.get_tick(),
            self._control_unit._programm_counter_register,
            self._control_unit._instruction_register.opcode,
            bool2int(self._control_unit._interruption_request),
            bool2int(self._control_unit._interruption_enabled),
            bool2int(self._control_unit._interruption_state),
            self._control_unit._data_path._accumulator_register,
            self._control_unit._data_path._buffer_register,
            self._control_unit._data_path._address_register,
            self._control_unit._data_path._read_memory(),
            bool2int(self._control_unit._data_path.negative()),
            bool2int(self._control_unit._data_path.zero())
        ) + device_state


    @staticmethod
    def parse_schedule(list_tuple_text: str) -> list[tuple[int, str]]:
        """Парсинг расписания ввода символов по тактам из текста с соответствующими данными."""
        list_schedule: list[tuple[int, str]] = list(eval(list_tuple_text)) if list_tuple_text.strip() != "" else []
        return list_schedule


    def simulation(self, code: Code, input_schedule: list[tuple[int, str]] = [], limit: int = 1000) -> tuple[str, int, int]:
        """Подготовка модели и запуск симуляции процессора.

        Возвращает вывод программы, значение счётчика команд и кол-во исполненных тактов.
        """
        assert limit > 0, "Simulation failed: Limit can not be negative or zero."
        self._common_memory[:len(code.contents)] = code.contents
        cur_schedule: int | None = 0 if len(input_schedule) > 0 else None
        try:
            while self._control_unit.get_tick() < limit:
                # Логика управлением расписания ввода
                if cur_schedule is not None and self._control_unit.get_tick() >= input_schedule[cur_schedule][0]:
                    self._io_controller._connected_devices[1]._data_register = ord(input_schedule[cur_schedule][1])
                    self._io_controller._connected_devices[1].signal_int_request()
                # Выполнение очередной инструкции
                self._control_unit.execute_next_command()
                logging.info(self.__repr__())
                # Сбор данных с устройств вывода
                if self._io_controller._connected_devices[2]._new_data:
                    new_symbol: str = chr(self._io_controller._connected_devices[2]._data_register)
                    self._output_buffer.append(new_symbol)
                    self._io_controller._connected_devices[2]._new_data = False
                    logging.info("output: '{}' << '{}'".format(self._output_buffer, new_symbol))
                    print(new_symbol, end="")
        except StopIteration:
            logging.info(self.__repr__())

        if self._control_unit.get_tick() >= limit:
            logging.warning("Instruction limit exceeded!")
        logging.info("Output buffer:\n" + repr("".join(self._output_buffer)))
        return ("".join(self._output_buffer),
                self._control_unit._programm_counter_register,
                self._control_unit.get_tick())


def main(code_file: str, input_file_name: str) -> None:
    """Функция запуска модели процессора. Параметры -- имена файлов с машинным
    кодом и с входными данными для симуляции ввода (формат [<такт подачи символа>, <символ>]).
    """
    machine: Machine
    code: Code

    try:
        code = read_code(code_file)
    except ValueError:
        # use logging.exception to see the stacktrace
        logging.error("Binary instructions can not be loaded properly.")
        return

    try:
        with open(input_file_name, encoding="utf-8") as file:
            input_text: str = file.read()
            input_schedule: list[tuple[int, str]] = Machine.parse_schedule(input_text)
            logging.info("Schedule: {}".format(input_schedule))
    except FileNotFoundError as e:
        logging.error(e)
        return

    io_devices: dict[int, IO.IODeviceCommon] = {index: IO.IODeviceCommon() for index in [1, 2]}
    io_devices.update({7: IO.IODeviceConsole()})
    machine = Machine(
        memory_size = len(code.contents),
        io_devices = io_devices
    )

    try:
        output, instr_counter, ticks = machine.simulation(
            code = code,
            input_schedule = input_schedule,
            limit = 4000
        )
    except ValueError as e:
        # use logging.exception to see the stacktrace
        logging.exception("Error: Instruction parameters are incorrect or instruction decoder doesn't know how to handle some instructions.")
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
    logging.getLogger().addHandler(logging.FileHandler("logs/machine.log"))
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    logging.info("====================\nExecution started...")
    main(code_file, input_file)
    logging.info("Execution ended.")
