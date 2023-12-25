section .data:
    msg:  db  13, 'Hello, world!';

section .bss:
    counter: db
    cur_symbol_addr: db

section .text:
_start:
    ld  db  msg
    st  db  counter
    ld  db  *msg
    st  db  cur_symbol_addr
    
loop:
    ld  db  cur_symbol_addr
    inc
    out
    ld  db  counter
    dec
    st  db  counter
    jnz loop
hlt
