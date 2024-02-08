section .data:
    msg:  12, "Hello world!";
    msg2: 1, "S" ; declared length doesn't match string literal length
    counter:          ; fix bss comment parsing
    cur_symbol_addr:        688

;section     text

;section A:sdsd;wrong section def
; :; bad label try
section .text:
_start:
    ld    msg;load the msg pointer
    st    counter
    ld    *msg ;load the msg value
    st    cur_symbol_addr
    
loop: ld    cur_symbol_addr
    inc
    out 0
    ld    counter
    dec
    st    counter
    jnz loop
hlt
