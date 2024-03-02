section .text:
_start:
    ld  dev_input
    st  int1
loop:
    eni
    nop
    jmp loop
dev_input:
    dii
    in  1
    out 3
    fi 
