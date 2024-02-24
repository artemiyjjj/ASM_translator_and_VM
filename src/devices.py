from __future__ import annotations


class IODevice:
    """ Сигналы и интерфейс для использования SPI-устройства.

    CS сигнал по умолчанию High. Low означает, что устройство в данный момент выбрано к обмену.
    Если устройство не выбрано, то оно должно игнорировать сигналы SCLK и MOSI (т.к. считается выключенным), а также отключить
    от шины сигнал MISO (подавать сигнал с высоким импедансом).

    Сигналы реализованы переменными, т.к. в рамках устройства сохраняют состояние до смены состояния
    """
    _interruption_request: bool
    _transfer_finished: bool
    _sclk: bool | None
    _cs: bool
    _mosi: bool | None
    _miso: bool | None

    _shift_register: int
    _step_counter: int

    def __init__(self) -> None:
        self._shift_register = 0
        self._step_counter = 0
        self._interruption_request = False
        self._transfer_finished = False
        self._sclk = None
        self._cs: bool = True
        self._mosi = None
        self._miso = None

    def signal_set_sclk(self, sclk_signal: bool) -> None:
        """ Передача сигнала SCLK, начало обмена, если сигнал поменялся на "1"."""
        if self._cs is False and self._sclk is not sclk_signal and sclk_signal is True:
            self._step_counter += 1
            if self._step_counter == 8:
                self._transfer_finished = True
            self._sclk = sclk_signal
            # Обмен данными по фронту
            assert self._mosi is not None
            assert self._miso is not None
            self._shift_register <<= 1
            self._miso = True if self._shift_register & 256 == 256 else False
            self._shift_register &= 255
            self._shift_register |= self._mosi

    def signal_set_cs(self, cs_signal: bool) -> None:
        self._cs = cs_signal
        # print("MOSI MISO before ", self._MOSI, " ", self._MISO)
        if cs_signal is True:
            self._mosi = self.miso = self._sclk = None
        else:
            self._mosi = self.miso = self._sclk = False
            # self._shift_register = 0
        # print("MOSI MISO after ", self._MOSI, " ", self._MISO)

    def signal_set_mosi(self, mosi_signal: bool) -> None:
        if self._cs is False:
            self._MOSI = mosi_signal


class SPIController:
    """ Контроллер управления передачей данных между машиной и переферийными устройствами
    
    """
    # Устройства, которые могут быть выбраны с помощью Chip Select
    _devices: dict[int, IODevice]

    # Сдвиговый регистр, последовательно передающий биты в MOSI
    _shift_register: int

    def __init__(self, slaves: dict[int, IODevice] = dict()) -> None:
        self._devices = slaves
        _shift_register = 0

    def signal_cs(self, chip_index: int, signal: bool) -> None:
        """ Демультиплексор для выбора устройства, на которое подать сигнал CS.

        Уровень сигнала поддерживается до смены."""
        if self._devices.get(chip_index) is not None:
            self._devices[chip_index].signal_set_cs(cs_signal = signal)

    def signal_sclk(self, signal: bool) -> None:
        """ Передача сигнала SCLK на линию SCLK (ко всем устройствам)."""
        for device in self._devices.values():
            device.signal_set_sclk(sclk_signal = signal)

    def signal_mosi(self, signal: bool) -> None:
        """ Передача сигнала MOSI на линию MOSI (ко всем устройствам)."""
        for device in self._devices.values():
            device.signal_set_mosi(mosi_signal = signal)
