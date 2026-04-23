from PIL import Image


# === GF(256) Arithmetic ===

def get_exp_table():
    global exp_table
    exp_table = []
    value = 1
    for i in range(255):
        exp_table.append(value)
        value = value * 2
        if value >= 256:
            value ^= 0x11d


def get_log_table():
    global log_table
    log_table = [0] * 256
    for i in range(255):
        log_table[exp_table[i]] = i


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return exp_table[(log_table[a] + log_table[b]) % 255]


def gf_add(a, b):
    return a ^ b


def gf_poly_mul(a, b):
    g = [0] * (len(a) + len(b) - 1)
    for i in range(len(a)):
        for j in range(len(b)):
            res = gf_mul(a[i], b[j])
            pos = i + j
            g[pos] = gf_add(g[pos], res)
    return g


def gf_poly_div(dividend, divisor):
    work = dividend.copy()
    for i in range(len(work) - 1, len(divisor) - 2, -1):
        coef = work[i]
        if coef != 0:
            for j in range(len(divisor)):
                work[i - len(divisor) + 1 + j] = gf_add(
                    work[i - len(divisor) + 1 + j],
                    gf_mul(coef, divisor[j])
                )
    return work[:len(divisor) - 1]


def gen_poly(r):
    g = [1]
    for i in range(0, r):
        g = gf_poly_mul(g, [exp_table[i], 1])
    return g


def rs_encode(data_bytes, r):
    g = gen_poly(r)
    reversed_data = data_bytes[::-1]
    shifted = [0] * r + reversed_data
    ec_reversed = gf_poly_div(shifted, g)
    return ec_reversed[::-1]


# === QR Code Tables ===

# (data_cw, ec_per_block, blocks_g1, data_per_g1, blocks_g2, data_per_g2)
QR_TABLE_M = {
    1: (16, 10, 1, 16, 0, 0),
    2: (28, 16, 1, 28, 0, 0),
    3: (44, 26, 1, 44, 0, 0),
    4: (64, 18, 2, 32, 0, 0),
    5: (86, 24, 2, 43, 0, 0),
    6: (108, 16, 4, 27, 0, 0),
}

ALIGNMENT_POSITIONS = {
    2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
}

FORMAT_INFO_M = {
    0: [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0],
    1: [1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1],
    2: [1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0],
    3: [1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1],
    4: [1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1],
    5: [1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0],
    6: [1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1],
    7: [1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0],
}

FINDER = [
    [1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 0, 1],
    [1, 0, 1, 1, 1, 0, 1],
    [1, 0, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1],
]

ALIGNMENT = [
    [1, 1, 1, 1, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 1, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 1],
]


# === Data Encoding ===

def get_qr_params(url):
    url_len = len(url)
    needed_bytes = (4 + 8 + url_len * 8 + 4 + 7) // 8
    for version in range(1, 7):
        data_cw = QR_TABLE_M[version][0]
        if needed_bytes <= data_cw:
            return version
    return None


def make_data_bytes(url_bytes, data_capacity):
    bit_stream = [0, 1, 0, 0]
    for bit in bin(len(url_bytes))[2:].zfill(8):
        bit_stream.append(int(bit))
    for byte in url_bytes:
        for bit in bin(byte)[2:].zfill(8):
            bit_stream.append(int(bit))
    bit_stream += [0, 0, 0, 0]
    while len(bit_stream) % 8 != 0:
        bit_stream.append(0)
    pads = [[1, 1, 1, 0, 1, 1, 0, 0], [0, 0, 0, 1, 0, 0, 0, 1]]
    pad_index = 0
    while len(bit_stream) < data_capacity * 8:
        bit_stream.extend(pads[pad_index])
        pad_index = (pad_index + 1) % 2
    data_bytes = []
    for i in range(0, len(bit_stream), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bit_stream[i + j]
        data_bytes.append(byte)
    return data_bytes


def encode_with_interleave(data_bytes, version):
    data_cw, ec_r, bg1, dpg1, bg2, dpg2 = QR_TABLE_M[version]

    # Split data into blocks
    blocks = []
    idx = 0
    for _ in range(bg1):
        blocks.append(data_bytes[idx:idx + dpg1])
        idx += dpg1
    for _ in range(bg2):
        blocks.append(data_bytes[idx:idx + dpg2])
        idx += dpg2

    # RS encode each block
    ec_blocks = []
    for block in blocks:
        ec = rs_encode(block, ec_r)
        ec_blocks.append(ec)

    # Interleave data blocks
    max_data_len = max(len(b) for b in blocks)
    interleaved_data = []
    for i in range(max_data_len):
        for block in blocks:
            if i < len(block):
                interleaved_data.append(block[i])

    # Interleave EC blocks
    interleaved_ec = []
    for i in range(ec_r):
        for block in ec_blocks:
            if i < len(block):
                interleaved_ec.append(block[i])

    return interleaved_data + interleaved_ec


def bytes_to_bits(byte_list):
    bits = []
    for byte in byte_list:
        for bit in bin(byte)[2:].zfill(8):
            bits.append(int(bit))
    return bits


# === QR Grid Building ===

def build_grid(version, final_bits, mask_num):
    size = 17 + version * 4
    grid = [[0] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    # Finder patterns
    for pos in [(0, 0), (0, size - 7), (size - 7, 0)]:
        for i in range(7):
            for j in range(7):
                grid[pos[0] + i][pos[1] + j] = FINDER[i][j]

    # Timing patterns
    for i in range(8, size - 8):
        grid[6][i] = (i + 1) % 2
        grid[i][6] = (i + 1) % 2

    # Alignment patterns
    if version >= 2:
        positions = ALIGNMENT_POSITIONS[version]
        for r in positions:
            for c in positions:
                if r < 9 and c < 9:
                    continue
                if r < 9 and c > size - 9:
                    continue
                if r > size - 9 and c < 9:
                    continue
                for i in range(5):
                    for j in range(5):
                        grid[r - 2 + i][c - 2 + j] = ALIGNMENT[i][j]

    # Dark module
    grid[size - 8][8] = 1

    # Reserve areas
    for i in range(9):
        for j in range(9):
            reserved[i][j] = True
    for i in range(9):
        for j in range(8):
            reserved[i][size - 8 + j] = True
    for i in range(8):
        for j in range(9):
            reserved[size - 8 + i][j] = True
    for i in range(8, size - 8):
        reserved[6][i] = True
        reserved[i][6] = True
    reserved[size - 8][8] = True
    if version >= 2:
        positions = ALIGNMENT_POSITIONS[version]
        for r in positions:
            for c in positions:
                if r < 9 and c < 9:
                    continue
                if r < 9 and c > size - 9:
                    continue
                if r > size - 9 and c < 9:
                    continue
                for i in range(5):
                    for j in range(5):
                        reserved[r - 2 + i][c - 2 + j] = True

    # Place data bits
    bit_index = 0
    going_up = True
    col = size - 1
    while col >= 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if going_up else range(size)
        for row in rows:
            for c in [col, col - 1]:
                if c >= 0 and not reserved[row][c] and bit_index < len(final_bits):
                    grid[row][c] = final_bits[bit_index]
                    bit_index += 1
        going_up = not going_up
        col -= 2

    # Apply mask
    for row in range(size):
        for col in range(size):
            if not reserved[row][col]:
                m = False
                if mask_num == 0:
                    m = (row + col) % 2 == 0
                elif mask_num == 1:
                    m = row % 2 == 0
                elif mask_num == 2:
                    m = col % 3 == 0
                elif mask_num == 3:
                    m = (row + col) % 3 == 0
                elif mask_num == 4:
                    m = (row // 2 + col // 3) % 2 == 0
                elif mask_num == 5:
                    m = (row * col) % 2 + (row * col) % 3 == 0
                elif mask_num == 6:
                    m = ((row * col) % 2 + (row * col) % 3) % 2 == 0
                elif mask_num == 7:
                    m = ((row + col) % 2 + (row * col) % 3) % 2 == 0
                if m:
                    grid[row][col] ^= 1

    # Place format info
    fb = FORMAT_INFO_M[mask_num]
    for i in range(6):
        grid[8][i] = fb[i]
    grid[8][7] = fb[6]
    grid[8][8] = fb[7]
    grid[7][8] = fb[8]
    for i in range(6):
        grid[5 - i][8] = fb[9 + i]
    for i in range(8):
        grid[size - 1 - i][8] = fb[i]
    for i in range(7):
        grid[8][size - 7 + i] = fb[8 + i]

    return grid, size


# === Mask Scoring ===

def score_mask(grid, size):
    penalty = 0
    for row in range(size):
        count = 1
        for col in range(1, size):
            if grid[row][col] == grid[row][col - 1]:
                count += 1
            else:
                if count >= 5:
                    penalty += count - 2
                count = 1
        if count >= 5:
            penalty += count - 2
    for col in range(size):
        count = 1
        for row in range(1, size):
            if grid[row][col] == grid[row - 1][col]:
                count += 1
            else:
                if count >= 5:
                    penalty += count - 2
                count = 1
        if count >= 5:
            penalty += count - 2
    for row in range(size - 1):
        for col in range(size - 1):
            val = grid[row][col]
            if val == grid[row][col + 1] == grid[row + 1][col] == grid[row + 1][col + 1]:
                penalty += 3
    dark = sum(grid[r][c] for r in range(size) for c in range(size))
    total = size * size
    pct = dark * 100 // total
    prev5 = abs((pct // 5) * 5 - 50) // 5
    next5 = abs(((pct // 5) + 1) * 5 - 50) // 5
    penalty += min(prev5, next5) * 10
    return penalty


def find_best_mask(version, final_bits):
    best_score = None
    best_mask = 0
    for mask_num in range(8):
        grid, sz = build_grid(version, final_bits, mask_num)
        score = score_mask(grid, sz)
        if best_score is None or score < best_score:
            best_score = score
            best_mask = mask_num
    return best_mask


# === Output ===

def save_qr_png(grid, size, filename="qr.png", scale=10, border=4):
    total = (size + 2 * border) * scale
    img = Image.new("1", (total, total), 1)
    for row in range(size):
        for col in range(size):
            if grid[row][col] == 1:
                for x in range(scale):
                    for y in range(scale):
                        img.putpixel(((col + border) * scale + x, (row + border) * scale + y), 0)
    img.save(filename)


# === Main ===

def main():
    get_exp_table()
    get_log_table()

    domain = input("Enter a full URL: ")

    version = get_qr_params(domain)
    if version is None:
        print("URL is too long for versions 1-6")
        return

    data_capacity = QR_TABLE_M[version][0]
    url_bytes = [ord(c) for c in domain]

    data_bytes = make_data_bytes(url_bytes, data_capacity)
    final = encode_with_interleave(data_bytes, version)
    final_bits = bytes_to_bits(final)

    mask_num = find_best_mask(version, final_bits)
    grid, sz = build_grid(version, final_bits, mask_num)

    save_qr_png(grid, sz, "qr.png")
    print(f"QR code saved! Version: {version}, Size: {sz}x{sz}, Mask: {mask_num}")


if __name__ == "__main__":
    main()
