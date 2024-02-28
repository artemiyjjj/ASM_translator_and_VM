section .data:
    msg:  12, "Hello world!";
    counter:          0
    cur_symbol_addr:        688
    cur_symb:   
    spi_counter: 

section .text:

_start:
    ld  print_out
    st  int4; init int vector

    ld    msg ;load the msg value
    inc
    st    cur_symbol_addr
     
loop: int   4
    ld      cur_symbol_addr
    inc
    st      cur_symbol_addr
    ld    counter
    inc
    st    counter
    jnz loop
hlt

print_out: 
    ld      0
    st      spi_counter
    out     0

    ld      **cur_symbol_addr
    st      cur_symb
out_loop:
    ld      *cur_symb
    out     1
    lsl
    st      cur_symb
    ld      0
    out     7
    ld      *spi_counter
    inc
    out     0
    st      spi_counter
    cmp     8
    jz      out_end
    jmp     out_loop
out_end:
    fi
