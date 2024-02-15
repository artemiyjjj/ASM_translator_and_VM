
# ASM. Транслятор и модель

- P33302, Романов Артемий Ильич
- asm | acc | neum | hw | tick | struct | trap | port | pstr | prob1 | spi
- С усложнением

## Язык программирования

### Расширенная форма Бэкуса-Наура

``` EnhancedBackusNaurForm
    programm ::= [section .data], section .text ;

    section .data ::=  (label, ":") (<amount of memory words> | <number>, ",", '"', <string>, '"' |
    <number | char>, {"," <number | char | string>}) ;

    section .text ::= <label _start>, ":", {statement}+ ;

    statement ::= [label, ":"], instruction | data defenition, [comment] ;

    instruction ::= no operand opcode | data manipulation opcode, data operand | control flow opcode, control flow operand ;

    no operand opcode ::= "hlt" | "eni" | "dii" | "inc" | "dec" | "nop" | "iret" ;

    unary opcode ::= data manipulation opcode | control opcode ;

    data manipulation opcode ::= "ld" | "st" | "add" | "sub" | "mul" | "div" | "cmp" | "or" | "and" | "out" | "in" ;

    control flow opcode ::= "jmp" | "jz" | "jnz" | "jn" | "jnn" | "int" ;

    operand ::= data operand | control flow operand ;

    data operand ::= number | dereference operator, <number> | <data label> | dereference operator, <data label> ;

    dereference operator ::= "*" ;

    control flow operand ::= <instruction label> ;

    label ::= (<letter> | "_") ({<letter> | <digit> | "_"}) ;

    data defenition ::= data size, ",", [data] ;

    data size ::= <positive integer number> ;

    data ::= <integer number> | '"', <str>, '"' ;

    comment ::= ";", {<any character except '"'>}* ;
```

Код программы выполняется последовательно. Одна инструкция определяет одну машинную команду.

Программа поделена на 2 секции: .data, .text. Каждая секция определяет определенную группу данных и располагается в отдельной части памяти компьютера, занимаемой программой. Поддерживается косвенный и прямой способы адресации - в первом случае, лэйбл или число будут интерпретированы непостредственно как адрес памяти, во втором случае - как значение, лежащее по этому лейблу или адресу.

- Секция .data содержит объявления и определения данных с уникальными лейблами. Можно располагать массивы данных одинкаового размера после одной общей метки через запятую.

- Секция .text содержит инструкции, определяющие операции, совершаемые программой, а также лейблы и комментарии.

Лейблы - названия буквенных меток, указывающих на какой-либо адрес в памяти. Заменяются числовыми адресами на этапе трансляции.

Инструкция может быть двух видов:

- без операндов (не требующая аргументов)

- унарной (требовать 1 аргумент)

Аргументы могут быть значениями, указателями на ячейку памяти и значениями по адресу ячейки памяти.  
По умолчанию, числа интерпретируются как значения, а лейблы как адреса. Для обращения интерпретации чисел как адресов, а лейблов - как значений по адресу, перед ними следуюет поставить символ "*".

Используемая стратегия вычислений в языке не одна. Доступен вызов по значению, т. е. при всех операциях происходит передача копий значений в аккумулятор; вызов по ссылке - операндом выступает ссылка на ячейку памяти, из которой необходимо извлечь значение. Вычисление (извлечение) выражения, находящегося по данному адресу в памяти происходит лениво - во время выполнения операции микроконтроллером.  
За счёт аккумуляторной архитектуры, на которой используется язык, и возможности управления памятью, вызов операций как по ссылке, так и по значению принципиально не отличаются между собой, т.к. ни одна операция, кроме ***store***, не изменяет содержимое памяти - только содержимое аккумулятора. Поэтому можно сказать, что стратегия вычислений - вызов по значению

Память выделяется статически, при запуске модели.  
Видимость данных (лейблов) - глобальная.  
Использование pstr с 4-байтовом префиксом возможно на этапе написания программы. Программист может объявлять данные, конкатенируя их через запятую после лейбла. Для объявления p-строки нужно сконкатенировать длину строки с самой строкой (см. файл [hello.asm](/examples/hello.asm)).

## Организация памяти

Модель памяти процессора:

- Общая память для команд и для данных.
- Машинное слово - 32 бита, знаковое.
- Линейное адресное пространство.
- Адресуемая единица памяти - 1 байт.

Механика отображения программы и данных на память:

- В начале каждой программы отведено **40 байт** (10 машинных слов) для хранения адресов на обработчики прерывания (8 адресов) + место для сохранения аккумулятора и счётчика команд перед прерыванием (2 машинных слова).
- Инструкция, имеющая метку **_start**, помещается в память по адресу **40**.
- Все инструкции, располагающиеся за этой меткой, помещаются в том же порядке, как в программе.
- Все инструкции, располагающиеся до этой метки, располагаются за уже расположенными инструкциями.
- Данные помещаются за всеми коммандами

## Система команд

Особенности процессора:

- Машинное слово - 32 бит, знаковое.
- Доступ к памяти осуществляется по адресу, хранящемуся в регистре AR (adress register)

## Набор инструкций

| Оператор | Инструкция | Операнды | Кол-во тактов | Описание |  
|---|---|---|---|---|  
| ld | Load | адрес | ? | Загрузка в аккумулятор значения из памяти по указанному адресу |  
| st | Store | адрес | ? | Запись в память по указанному адресу значения из аккумулятора |
| add | Addition | значение по адресу / значение | ? | Сложение значения параметра с значением из аккумулятора с последующей записью результата в аккумулятор |  
| sub | Substraction | значение по адресу / значение | ? | Вычитание значения параметра из значения из аккумулятора с последующей записью результата в аккумулятор |  
| mul | Multiplication | значение по адресу / значение | ? | Умножение значения параметра с значением из аккумулятора с последующей записью в аккумулятор |  
| div | Division | значение по адресу / значение | ? | Деление значения из аккумулятора с значением параметра с последующей записью в аккумулятор |  
| or | Logical "Or" | значение по адресу / значение | ? | Логическое "ИЛИ" между аккумулятором и значением параметра с последующей записью результата в аккумулятор. |  
| and | Logical "And" | значение по адресу / значение | ? | Логическое "И" между аккумулятором и значением параметра с последующей записью в аккумулятор. |  
| jmp | Jump | адрес / значение по адресу | ? | Безусловное изменение значения регистра-указателя команд (IP) на значение параметра. |  
| jz | Jump if Zero | адрес / значение по адресу | ? | Изменение значения регистра IP на значение параметра при значении 1 в регистре Z. |  
| jnz | Jump if Not Zero | адрес / значение по адресу | ? | Изменение значения регистра IP на значение параметра при значении 0 в регистре Z. |  
| jn | Jump if Negative | адрес / значение по адресу | ? | Изменение значения регистра IP на значение параметра при значении 1 в регистре N. |  
| jp | Jump if Positive | адрес / значение по адресу | ? | Изменение значения регистра IP на значение параметра при значении 0 в регистре N. |  
| int | interuption | _ | ? | Вызов определенного вектора прерываний |  
| eni | enable interution | - | ? | Разрешить прерывания |  
| dii | disable interuption | - | ? | Запретить прерывания |  
| fi | finish interruption | - | ? | Завершить обработку прерывания, вернуть AC и PC в состояние "как до прерывания" |  
| nop | no operation | - | ? | Ничего не выполнять |
| hlt | halt | - | ? | Остановить работу машины |

## Кодирование инструкций

- Машинный код сериализуется в список формата JSON.
- Один элемент списка - одна машинная инструкция.
- Индекс списка - адрес инструкции в памяти и адрес инструкции в машинном коде. Используется для команд перехода.

Пример:

``` machine code
[
    {
        "index": 0,
        "opcode": "jmp",
        "arg": 1,
        "mode": "deref",
        "line": 2
    },
    {
        "index": 1,
        "label": "a",
        "value": "x",
        "line": 4
    }
]
```

В примере, представленом выше:

- opcode - строка с кодом инструкции.
- arg - аргумент, если имеется.
- position - местоположение инструкции в исходном коде программы.

Типы данных для реализации инструкций (файл [isa.py](/src/isa.py)):

- Opcode - перечисление кодов инструкций.
- StatementTerm - структура для описания местоположения позиции инструкции в исходном коде. ???

## Транслятор

...

Примечание: вопросы отображения переменных на регистры опущены из-за отсутствия таковых.

## Модель процессора

### DataPath

...

### Control Umit


## Тестирование


