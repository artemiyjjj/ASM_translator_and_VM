section .text:
_start:
    ld  db  msg
    st  db  counter
    
loop:
    
    jnz loop


section .data:
    msg:     db     13, 'Hello, world!';

section .bss:
    counter: db
    cur_symbol: db
