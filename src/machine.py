class DataPath:
    # AC регистр
    accumulator_reg: int = None

    # AR регистр
    adress_reg: int = None

    # Буффер входных данных
    input_buffer: int = None



    def signal_output(self) -> void:



class ControlUnit:

    def tick(self) -> void:


    def perform_next_tick(self) -> void:
        """ Выполнение следующего процессорного такта.
        
        """

    def __perp__(self) -> str:
        """ Вернуть состояние процессора в строковом представлении. 
        """


class Machine:
    common_memory: list[int]
    data_path: DataPath
    control_unit: ControlUnit


    def __init__(self, memory_size, input_biffer):
        assert memory_size > 0, "Memory size should not be zero"
        self.common_memory = [0] * memory_size
        self.data_path = 
        self.control_unit = 

    def simulation(code: Code, tokens, memory_size, limit: int) -> str:
        return ""

    def main(code: Code, input_file: file) -> void:

