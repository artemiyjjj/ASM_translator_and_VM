max: int = 1000
sum: int = 0
x1: int = 3
x2: int = 5

for i in range(0, max):
    if i % x1 == 0:
        sum += i
        continue
    if i % x2 == 0:
        sum += i

print(sum)
