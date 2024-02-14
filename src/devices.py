from abc import ABC, abstractmethod
import BitVector

def get_spi_shift_reg_length() -> int:
    """ Количество битов в сдвиговых регистрах устройств SPI."""
    return 8

class SPISlave(ABC):
    """ Абстрактный класс для объявления методов SPI-slave'а

    Объявляет методы, необходимые к реализации имплементирующим классом,
     и определяет методы для использования SPI-устройства.

    CS сигнал по умолчанию High. Low означает, что устройство в данный момент выбрано к обмену.
    Если устройство не выбрано, то оно должно игнорировать сигналы SCLK и MOSI, а также отключить
    от шины сигнал MISO (подавать сигнал с высоким импедансом).
    """
    _SCLK: bool | None = False
    _CS: bool = True
    _MOSI: bool | None = None
    _MISO: bool | None = None

    _timer: int = 0

    _shift_register: BitVector = BitVector(size = get_spi_shift_reg_length())

    # def cycle():

    def set_SCLK(self, SCLK_signal: bool) -> bool:
        self._SCLK = SCLK_signal if self._CS == False else None

    def set_CS(self, CS_signal: bool) -> bool:
        self._CS = CS_signal
        print("MOSI MISO before ", self._MOSI, " ", self._MISO)
        self._MOSI, self._MISO = None if CS_signal == True else self._MOSI, self._MISO
        print("MOSI MISO after ", self._MOSI, " ", self._MISO)

    def set_MISO(self, MISO_signal: bool) -> bool:
        self._MISO = MISO_signal if self._CS == False else None

    def set_MOSI(self, MOSI_signal: bool) -> bool:
        self._MOSI = MOSI_signal if self._CS == False else None

class SPIMaster(ABC):
    """ Абстрактный класс для объявления методов SPI-master'а

    Объявляет методы, необходимые к реализации имплементирующим классом,
     и определяет методы для использования SPI-устройства.
    """
    # Устройства, которые могут быть выбраны с помощью Chip Select
    _devices: list[SPISlave] | None = None

    # Счётчик смен сигнала SCLK (переданных бит)
    _timer: int = 0

    # Сдвиговый регистр, последовательно передающий биты в MOSI
    _shift_register: BitVector = BitVector(size = get_spi_shift_reg_length())


    def __init__(self) -> None:
        print("SPI MASTER INIT")

    def send_signals(self, chip_index: int, bit: bool) -> None:
        self.SCLK()
        self.CS(chip_index)
        self.MOSI(bit)
        self.MISO()
        _timer += 1

    def SCLK(self) -> None:
        for device in self.devices:
            device.set_SCLK

    def CS(self, chip_index: int) -> None:
        for device_index, device in enumerate(self.devices):
            signal: bool = False if device_index == chip_index else True
            device.set_CS(signal)

    def MOSI(self, bit: bool) -> None:
        pass

    def MISO(self) -> None:
        pass




class IODevice(SPISlave):
    data_reg
    interruption_request:


class SPIController(SPIMaster):
    """ Контроллер управления передачей данных между машиной и переферийными устройствами
    
    """

    def __init__(self) -> None:
        super().__init__()

    def __init__(self, devices: list[IODevice]) -> None:


