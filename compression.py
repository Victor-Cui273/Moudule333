"""
Elias gamma, delta 编码 / 解码
Golomb 编码 / 解码
"""

class EliasCodec:
    @staticmethod
    def gamma_encode(n: int) -> str:
        """返回二进制字符串，用于演示或存储"""
        if n < 1:
            raise ValueError("n must be >= 1")
        binary = bin(n)[2:]          # 去掉 '0b'
        prefix = '0' * (len(binary) - 1)
        return prefix + binary

    @staticmethod
    def gamma_decode(bit_str: str) -> tuple:
        """解码，返回 (解码后的整数, 消耗的位数)"""
        # 先读取连续 '0' 直到遇到 '1'
        k = 0
        while k < len(bit_str) and bit_str[k] == '0':
            k += 1
        if k >= len(bit_str):
            raise ValueError("Invalid gamma code")
        # 然后读取接下来的 k+1 位（包括第一个 1）
        total_len = 2 * k + 1
        if total_len > len(bit_str):
            raise ValueError("Incomplete gamma code")
        code = bit_str[:total_len]
        # 解码：前缀的0个数 = k，后面的二进制数 = code[k:]
        value = int(code[k:], 2)   # 因为 code[0:k] 全是0，跳过
        return value, total_len

    @staticmethod
    def delta_encode(n: int) -> str:
        """Elias delta 编码"""
        if n < 1:
            raise ValueError("n must be >= 1")
        binary = bin(n)[2:]
        L = len(binary)
        gamma_of_L = EliasCodec.gamma_encode(L)
        return gamma_of_L + binary[1:]   # 去掉最高位

    @staticmethod
    def delta_decode(bit_str: str) -> tuple:
        """解码，返回 (值, 消耗位数)"""
        # 先解码 L (即二进制长度的长度)
        L_val, consumed1 = EliasCodec.gamma_decode(bit_str)
        # 然后读取后面 L_val - 1 位
        if consumed1 + L_val - 1 > len(bit_str):
            raise ValueError("Incomplete delta code")
        binary_part = '1' + bit_str[consumed1:consumed1 + L_val - 1]
        value = int(binary_part, 2)
        return value, consumed1 + (L_val - 1)

    @staticmethod
    def encode_int_list(ints, method='gamma') -> bytes:
        """将整数列表压缩为字节串"""
        bit_str = ''
        for n in ints:
            if method == 'gamma':
                bit_str += EliasCodec.gamma_encode(n)
            elif method == 'delta':
                bit_str += EliasCodec.delta_encode(n)
            else:
                raise ValueError("method must be 'gamma' or 'delta'")
        # 补齐到 8 的倍数
        padding = (8 - len(bit_str) % 8) % 8
        bit_str += '0' * padding
        return int(bit_str, 2).to_bytes((len(bit_str) + 7) // 8, byteorder='big'), padding

    @staticmethod
    def decode_bytes(data: bytes, padding: int, method='gamma'):
        """从字节串解码回整数列表"""
        bit_str = bin(int.from_bytes(data, byteorder='big'))[2:].zfill(len(data)*8)
        if padding:
            bit_str = bit_str[:-padding]
        result = []
        i = 0
        while i < len(bit_str):
            if method == 'gamma':
                val, consumed = EliasCodec.gamma_decode(bit_str[i:])
            else:
                val, consumed = EliasCodec.delta_decode(bit_str[i:])
            result.append(val)
            i += consumed
        return result


class GolombCodec:
    @staticmethod
    def encode(n: int, m: int) -> str:
        """
        Golomb 编码，m 为参数（正整数）
        对于 n >= 0
        商 q = n // m, 余数 r = n % m
        输出: q 个 1 后跟一个 0，加上 r 的编码（长度为 ceil(log2(m)) 或 floor(log2(m))）
        """
        if n < 0:
            raise ValueError("n must be >= 0")
        if m <= 0:
            raise ValueError("m must be > 0")
        q = n // m
        r = n % m
        # 商部分：q 个 1 后加 0
        unary = '1' * q + '0'
        # 余数部分：变长编码
        b = m.bit_length()
        threshold = (1 << b) - m
        if r < threshold:
            r_bits = bin(r)[2:].zfill(b - 1)
        else:
            r_bits = bin(r + threshold)[2:].zfill(b)
        return unary + r_bits

    @staticmethod
    def decode(bit_str: str, m: int) -> tuple:
        """解码，返回 (值, 消耗位数)"""
        # 读商：连续 1 直到遇到 0
        q = 0
        i = 0
        while i < len(bit_str) and bit_str[i] == '1':
            q += 1
            i += 1
        if i >= len(bit_str) or bit_str[i] != '0':
            raise ValueError("Invalid Golomb code")
        i += 1  # 跳过 0
        # 读余数
        b = m.bit_length()
        threshold = (1 << b) - m
        # 先尝试读 b-1 位
        if i + b - 1 > len(bit_str):
            raise ValueError("Incomplete Golomb code")
        first_bits = bit_str[i:i + b - 1]
        r = int(first_bits, 2) if first_bits else 0
        if r >= threshold:
            # 需要再读一位
            if i + b > len(bit_str):
                raise ValueError("Incomplete Golomb code")
            additional_bit = bit_str[i + b - 1]
            r = (r << 1) | int(additional_bit)
            consumed = i + b
        else:
            consumed = i + b - 1
        n = q * m + r
        return n, consumed

    @staticmethod
    def encode_list(ints, m) -> bytes:
        bit_str = ''
        for n in ints:
            bit_str += GolombCodec.encode(n, m)
        padding = (8 - len(bit_str) % 8) % 8
        bit_str += '0' * padding
        return int(bit_str, 2).to_bytes((len(bit_str) + 7) // 8, byteorder='big'), padding

    @staticmethod
    def decode_bytes(data: bytes, padding: int, m):
        bit_str = bin(int.from_bytes(data, byteorder='big'))[2:].zfill(len(data)*8)
        if padding:
            bit_str = bit_str[:-padding]
        result = []
        i = 0
        while i < len(bit_str):
            n, consumed = GolombCodec.decode(bit_str[i:], m)
            result.append(n)
            i += consumed
        return result