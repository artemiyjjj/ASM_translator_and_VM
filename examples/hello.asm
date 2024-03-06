section .data:
    message: 12, "Hello World!"
    output_counter: 0
    output_position: 0
section .text:
_start:
    ld  message
    st  output_position
loop:
    ld *output_position
    inc
    st  output_position
    ld  **output_position
    out 3
    ld  *output_counter
    inc
    st  output_counter
    cmp *message
    jnz loop
    hlt