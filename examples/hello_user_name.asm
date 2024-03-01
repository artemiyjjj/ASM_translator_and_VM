section .data:
    question: 18, "What is your name?"
    answer1: 7, "Hello, "
    answer2: 1, "!"
    user_input: 40,
    input_end_symbol: 10 ; "\n" ascii code
    input_counter:  0
    input_position: 0
    output_counter: 0
    output_position: 0
    printing_literal_len: 0
    return_address: 0
section .text:
_start:
    ld  question
    st  output_position
    st  printing_literal_len
    ld  0
    st  output_counter
    ld  prepare_read_input
    st  return_address
; set output_position, printing_literal_len and return_address before jmp
print_literal:
    ld  *output_position
    inc
    st  output_position
    ld  **output_position
    out 3
    ld  *output_counter
    inc
    st  output_counter
    cmp *printing_literal_len
    jnz print_literal
    ; finish printing
prepare_read_input:
    ld  0
    st  output_counter
    ld  user_input
    inc             ; save memory for len
    st  input_position
read_input:
    in  13
    cmp *input_end_symbol   ;че грузит в буффер при *? Должен значение по адресу
    jz  store_input_len
    st  *input_position
    ld  *input_position
    inc
    st  input_position
    ld  *input_counter
    inc
    st  input_counter
    jmp read_input
store_input_len:
    ld  *input_counter
    st  user_input
    ; finish input
prepare_print_answer1:
    ld  0
    st  input_counter
    ld  answer1
    st  output_position
    st  printing_literal_len
    ld  prepare_print_user_input
    st  return_address
    jmp print_literal
prepare_print_user_input:
    ld  0
    st  output_counter
    ld  user_input
    st  output_position
    st  printing_literal_len
    ld  prepare_print_answer2
    st  return_address
    jmp print_literal
prepare_print_answer2:
    ld  0
    st  output_counter
    ld  answer2
    st  output_position
    st  printing_literal_len
    ld  exit
    st  return_address 
    jmp print_literal
exit:
    hlt
    