a = [None]*10
a = [None, 1, 2, 3, 4, 5, 6 ,7, 8, None] 

idx = 0
b = []
for chunk in a:
    if chunk is None:
        b.append(idx)
    idx += 1


print(b)