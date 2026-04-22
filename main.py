domain = "https://www.youtube.com/"
r = 22

def qr_field(version):
    global size, reserved
    size = 17 + version * 4
    grid = [[0] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]
    return grid

finder = [
    [1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1],
    [1,0,1,1,1,0,1],
    [1,0,1,1,1,0,1],
    [1,0,1,1,1,0,1],
    [1,0,0,0,0,0,1],
    [1,1,1,1,1,1,1]
]

alignment = [
    [1,1,1,1,1],
    [1,0,0,0,1],
    [1,0,1,0,1],
    [1,0,0,0,1],
    [1,1,1,1,1]
]


def get_ord(i:str) -> list[int]:
    asci = []
    for char in i:
        asci.append(ord(char))

    return asci

def r_shift(l:list[int]) -> list[int]:
    d = [0] * r
    for i,val in enumerate(l):
        d.append(val)
    return d

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

def gf_poly_div(dividend:list[int], divisor:list[int]) -> list[int]:
    work = dividend.copy()
    for i in range(len(work) - 1, len(divisor) - 2, -1):
        coef = work[i]
        if coef != 0:
            for j in range(len(divisor)):
                work[i - len(divisor) + 1 + j] = gf_add(work[i - len(divisor) + 1 + j], gf_mul(coef, divisor[j]))

    return work[:len(divisor) - 1]

def sys_rs(control,ord):
    d = control.copy()
    for i, val in enumerate(ord):
        d.append(val)
    return d


def get_qr_version(i:list[int]) -> int:
    bites = len(i)
    if bites <= 14:
        return 1
    elif bites <=26:
        return 2
    elif bites <= 42:
        return 3
    elif bites <= 62:
        return 4
    elif bites <= 84:
        return 5
    elif bites <= 106:
        return 6
    else:
        return 0

# qr needs

def qr_finders(grid:list[list[int]],row:int,col:int):
    for i in range(7):
        for j in range(7):
            grid[row + i][col + j] = finder[i][j]
            reserved[row + i][col + j] = True

def qr_aligments(grid,version):
    if version >= 2:
        for i in range(5):
            for j in range(5):
                grid[20 + i ][20 + j] = alignment[i][j]
                reserved[20 + i][20 + j] = True

def qr_dark_module(grid):
    grid[size - 8][8] = 1
    reserved[size - 8][8] = True



def qr_timing_patterns(grid:list[list[int]]):
    for i in range(8, size - 8):
        grid[6][i] = (i + 1) % 2
        grid[i][6] = (i + 1) % 2
        reserved[6][i] = True
        reserved[i][6] = True


def get_qr_with_finders(grid):
    qr_finders(grid, 0,0)
    qr_finders(grid, 0,size - 7)
    qr_finders(grid, size - 7, 0)


    return grid


# qr data
def bits(i:list[int]) -> list[int]:
    data_bites = []
    data_info_bites = [0,1,0,0]


    for byte in i:
        for bit in bin(byte)[2:].zfill(8):
            data_bites.append(int(bit))

    for bit in bin(len(i))[2:].zfill(8):
        data_info_bites.append(int(bit))

    return data_info_bites + data_bites + [0,0,0,0]

def reserve_areas():
    # levý horní 9x9
    for i in range(9):
        for j in range(9):
            reserved[i][j] = True
    # pravý horní 9x8
    for i in range(9):
        for j in range(8):
            reserved[i][size - 8 + j] = True
    # levý dolní 8x9
    for i in range(8):
        for j in range(9):
            reserved[size - 8 + i][j] = True


def place_data(grid, data_bits):
    bit_index = 0
    going_up = True
    col = size - 1

    while col >= 0:
        if col == 6:
            col -= 1

        if going_up:
            rows = range(size - 1, -1, -1)
        else:
            rows = range(size)

        for row in rows:
            for c in [col, col - 1]:  # pravý, pak levý
                if not reserved[row][c] and bit_index < len(data_bits):
                    grid[row][c] = data_bits[bit_index]
                    bit_index += 1

        going_up = not going_up
        col -= 2

def main():
    get_exp_table()
    get_log_table()

    shifted = r_shift(get_ord(domain))
    g = gen_poly()
    remainder = gf_poly_div(shifted, g)
    codeword = sys_rs(remainder, get_ord(domain))

    grid = qr_field(get_qr_version(codeword))

    get_qr_with_finders(grid)
    qr_timing_patterns(grid)
    qr_aligments(grid,get_qr_version(codeword))
    qr_dark_module(grid)
    place_data(grid,bits(codeword))

    for row in grid:
        print("".join("██" if cell == 1 else "  " for cell in row))

    print(len(bits(codeword)))



if __name__ == "__main__":
    main()
