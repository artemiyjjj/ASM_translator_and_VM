section .data:
    greeting: 6, "Hello!"
    input: 5, ; допустим ожидается ввод 5 символов
    in_ptr: 0
    out_counter: 0
    CLK_counter: 0

    ; 0 - SCLK
    ; 1 - MOSI
    ; 2 - MISO
    ; 3 - CS - in dev
    ; 4 - CS - out dev
section .text:
    _start:
        ld input
        st in_ptr
        eni
        int int_out
        
    ; SPI:
    ; - mode = 1
    ; CPOL = 0: исходный SCLK - low
    ; CPHA = 1: выборка данных по заднему фронту SCLK
    int_in:
        ld  0
        st in_counter
        st  CLK_counter
        out 0 ; сигнал CLK
        ; что делать с таймером (разницей в частоте устройства и процессора): надо какие то прерывания
        out 1 ; сигнал CS
    in_loop:
        ld CLK_counter ; значение по адресу
        inc
        st CLK_counter
        mod 2
        out 0
        ; ввод происходит по биту
        ld  **in_ptr ; загрузка имеющихся битов данных
        lsl ; сдвиг влево для освобождения места
        in 2 ; получение нового бита
        st *in_ptr ; сохранение
        ld in_counter ; увеличение сч   тчикс 
        inc
        cmp 8
        st in_counter
        jnz in_loop
        ld *in_ptr
        inc
        st in_ptr
        fi

    int_out:
        