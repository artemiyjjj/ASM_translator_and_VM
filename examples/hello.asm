section .data:
    msg:  13, 'Hello, world!';

section .bss:
    counter:        1   ; fix bss comment parsing
    cur_symbol_addr:        1

section .text:
_start:
    ld    msg
    st    counter
    ld    *msg
    st    cur_symbol_addr
    
loop: ld    cur_symbol_addr
    inc
    out 0
    ld    counter
    dec
    st    counter
    jnz loop
hlt
