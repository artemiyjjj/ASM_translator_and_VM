def prob1_test() -> int:  # noqa: INP001
    max_val: int = 1000
    st_sum: int = 0
    x1: int = 3
    x2: int = 5

    for i in range(0, max_val):
        if i % x1 == 0:
            st_sum += i
            continue
        if i % x2 == 0:
            st_sum += i

    return st_sum
