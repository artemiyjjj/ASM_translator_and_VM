section .data:
    label: 1, "A"
    num:
    num_def: 559
section .text:
    _start:
    ld      *num_def
    add     4
    inc
    mod     5
    st      num
    hlt