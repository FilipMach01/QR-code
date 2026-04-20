domain = "https://www.youtube.com/"
r = 4

def get_ord(i:str) -> list[int]:
    asci = []
    for char in i:
        asci.append(ord(char))

    return asci

def get_exp_table() -> list[int]:
    global exp_table
    exp_table = []
    value = 1

    for i in range(255):
        exp_table.append(value)
        value = value * 2
        if value >= 256:
            value ^= 0x11d

    return exp_table

def get_log_table() -> list[int]:
    global log_table
    log_table = [0] * 256

    for i in range(255):
        log_table[exp_table[i]] = i

    return log_table

def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return exp_table[(log_table[a] + log_table[b]) % 255]

def gf_add(a, b):  #XOR
    return a ^ b

def gf_poly_mul(a:list[int], b:list[int]) -> list[int]:
    g = [0] * (len(a) + len(b) - 1)

    for i in range(len(a)):
        for j in range(len(b)):
            res = gf_mul(a[i], b[j])
            pos = i + j
            g[pos] = gf_add(g[pos],res)

    return g

def gen_poly():
    g = [1]
    for i in range(1, r + 1):
        g = gf_poly_mul(g, [exp_table[i], 1])

    return g



print(get_ord(domain))
print(get_exp_table())
print(get_log_table())
print(gf_mul(5,6))
print(gf_poly_mul([2,3,4],[5,6,2]))
print(gen_poly())