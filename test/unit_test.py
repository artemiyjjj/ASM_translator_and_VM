@pytest.mark.golden_test("golden_tests/unit/translator.yml")
def test_translator(golden, caplog) -> void:
    """ Golden tests для транслятора.
    """

@pytest.mark.golden_test("golden_tests/unit/machine.yml")
def test_machine(golden, caplog) -> void:
    """ Golden tests модели компьютера.
    """