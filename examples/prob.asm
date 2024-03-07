section .data:
    sum:    0
    max:    1000     
    cur:    0
    tmp:   
    print_loop_count:   4
    cur_print_loop:     0
section .text:
_start:
    ld      *cur
    mod     3
    jnz     sec
    ld      *sum
    add     *cur
    st      sum
    jmp     end
sec:
    ld      *cur
    mod     5
    jnz     end
    ld      *sum
    add     *cur
    st      sum
end:
    ld      *cur
    inc
    st      cur
    cmp     *max
    jnz     _start
; result is 4 bytes, i/o takes byte
; interpret chars given to out put as 4 byte signed number
print_new_byte:
    ld      *sum
    st      tmp
    ld      *print_loop_count
    dec
    st      print_loop_count
    ld      0
    st      cur_print_loop
next_iter:
    cmp     *print_loop_count
    jnz     shift
    ld      *tmp
    out     3
next_byte:
    ld     *print_loop_count
    jnz     print_new_byte
exit:
    hlt
shift:
    ld      *tmp
    asr
    asr
    asr
    asr
    asr
    asr
    asr
    asr
    st      tmp
    ld      *cur_print_loop
    inc 
    st      cur_print_loop
    jmp     next_iter
