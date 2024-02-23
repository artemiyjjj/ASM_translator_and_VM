section .data:
    sum:    0
    max:    1000     
    cur:    0
    tmp:   

section .text:
    _start:
    ld      cur
    mod     3
    jnz     sec
    ld      sum
    add     cur
    st      sum
    jmp     end
sec:ld      cur
    mod     5
    jnz     end
    ld      sum
    add     cur
    st      sum
end:
    ld      cur
    inc
    st      cur
    cmp     max
    jnz     _start
    ld      sum
    ; 4 bytes
    out     ??? ; where???
    out     ???
    out     ???
    out     ???
    hlt
    