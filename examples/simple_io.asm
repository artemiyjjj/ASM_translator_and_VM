section .data:
    symb: 1, 

section .text:
;interruption_dev:
 ;   in  0
_start:
    in  13
    st  symb
    out 3
    hlt