section .data:
    letter_count: 3
section .text:
_start:
    ld  dev_input
    st  int1
loop:
    eni
    ld  letter_count
    cmp 0
    jz  exit
    jmp loop
exit:
    hlt
dev_input:
    dii
    in  1
    out 3
    ld  *letter_count
    inc
    st  letter_count
    fi 
