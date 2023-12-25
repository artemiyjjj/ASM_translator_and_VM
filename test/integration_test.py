
@pytest.mark.golden_test("golden_tests/*.yml")
def test_translator_and_machine(golden, caplog) -> void:
    """ Golden tests для транслятора и модели компьютера.
    """
