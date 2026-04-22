domain = input("Enter a full url adress: ")
r = 26

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

FORMAT_INFO_M = {
    0: [1,0,1,0,1,0,0,0,0,0,1,0,0,1,0],
    1: [1,0,1,0,0,0,1,0,1,1,0,0,1,0,1],
    2: [1,0,1,1,1,1,0,1,1,0,0,1,0,0,0],
    3: [1,0,1,1,0,1,1,1,0,1,1,1,1,1,1],
    4: [1,0,0,0,1,0,1,1,0,1,0,1,1,0,0],
    5: [1,0,0,0,0,0,0,1,1,0,1,1,0,1,1],
    6: [1,0,0,1,1,1,1,0,1,1,1,0,1,1,0],
    7: [1,0,0,1,0,1,0,0,0,0,0,0,0,0,1],
}

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
    for i in range(0, r):
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


def get_qr_version(data):
    length = len(data)
    if length <= 16: return 1
    elif length <= 28: return 2
    elif length <= 44: return 3
    elif length <= 64: return 4
    elif length <= 86: return 5
    elif length <= 108: return 6
    else: return 0



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

def make_data_bytes(url_bytes):
    # kroky 1-4 (to co už máš)
    bit_stream = [0, 1, 0, 0]  # mode indicator

    for bit in bin(len(url_bytes))[2:].zfill(8):  # character count
        bit_stream.append(int(bit))

    for byte in url_bytes:  # data
        for bit in bin(byte)[2:].zfill(8):
            bit_stream.append(int(bit))

    bit_stream += [0, 0, 0, 0]  # terminator

    # krok 5 — padding
    while len(bit_stream) % 8 != 0:  # zarovnat na celý bajt
        bit_stream.append(0)

    pads = [[1, 1, 1, 0, 1, 1, 0, 0], [0, 0, 0, 1, 0, 0, 0, 1]]
    pad_index = 0
    while len(bit_stream) < 352:  # 44 bajtů = 352 bitů
        bit_stream.extend(pads[pad_index])
        pad_index = (pad_index + 1) % 2


    data_bytes = []
    for i in range(0, len(bit_stream), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bit_stream[i + j]
        data_bytes.append(byte)

    return data_bytes

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

def apply_mask(grid):
    for row in range(size):
        for col in range(size):
            if not reserved[row][col]:
                if (row + col) % 2 == 0:
                    grid[row][col] ^= 1


def place_format_info(grid,mask=0):
    format_bits = FORMAT_INFO_M[mask]


    for i in range(6):
        grid[8][i] = format_bits[i]

    grid[8][7] = format_bits[6]

    grid[8][8] = format_bits[7]

    grid[7][8] = format_bits[8]

    for i in range(6):
        grid[5 - i][8] = format_bits[9 + i]


    for i in range(8):
        grid[size - 1 - i][8] = format_bits[i]

    for i in range(7):
        grid[8][size - 7 + i] = format_bits[8 + i]

from PIL import Image

def save_qr_png(grid, filename="qr.png", scale=10, border=4):
    s = len(grid)
    total = (s + 2 * border) * scale
    img = Image.new("1", (total, total), 1)
    for row in range(s):
        for col in range(s):
            if grid[row][col] == 1:
                for x in range(scale):
                    for y in range(scale):
                        img.putpixel(((col + border) * scale + x, (row + border) * scale + y), 0)
    img.save(filename)

def rs_encode(data_bytes):
    g = gen_poly()
    reversed_data = data_bytes[::-1]
    shifted = [0] * r + reversed_data
    ec_reversed = gf_poly_div(shifted, g)
    return ec_reversed[::-1]

def main():
    get_exp_table()
    get_log_table()

    data_bytes = make_data_bytes(get_ord(domain))


    ec_bytes = rs_encode(data_bytes)

    final = data_bytes + ec_bytes  # 70 bajtů


    final_bits = []
    for byte in final:
        for bit in bin(byte)[2:].zfill(8):
            final_bits.append(int(bit))

    version = get_qr_version(data_bytes)
    grid = qr_field(version)

    get_qr_with_finders(grid)
    qr_timing_patterns(grid)
    qr_aligments(grid, version)
    qr_dark_module(grid)
    reserve_areas()
    place_data(grid, final_bits)
    apply_mask(grid)
    place_format_info(grid)

    for row in grid:
        print("".join("█" if cell == 1 else " " for cell in row))


    print(len(final_bits))
    print(size)
    print(version)
    save_qr_png(grid, "/home/filip/workspace/QRcode/qr.png")



if __name__ == "__main__":
    main()
