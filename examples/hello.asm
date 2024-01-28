section .data:
    msg:  13, 'Hello world!';
    msg2: 1, 'Simple text' ; declared length doesn't match string literal length
    counter:        1,   ; fix bss comment parsing
    cur_symbol_addr:        1,

;section     text

;section A:sdsd;wrong section def
: ; bad label try
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
