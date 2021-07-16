from typing import List


class ConvolutionalCode:
    """The code assumes zero state termination, and k=1"""

    def __init__(self, generators: tuple):
        """
        :param generators: each element in the tuple represents a single generator polynomial. The convention
        we use is: 1+D=b011=3 (and not 1+D=6)
        """
        self.tup = generators
        self.gen_list = [bin(i)[2:] for i in self.tup]
        self.K = len(max(self.gen_list, key=len)) - 1  # constraint length
        self.reg = [0 for i in range(self.K)]

    def encode(self, data: bytes) -> List[int]:
        """
        encode input data bytes. Uses zero tail termination
        :param data: data to be encoded
        :return: encoded data
        :rtype: List[int]
        """
        # Generating the binary sequence and adding up a constraint length of trailing zeros.
        in_bin = ''
        for i in range(len(data)):
            in_bin += f'{data[i]:0>8b}'
        in_bin = (in_bin + self.K * '0')

        # # the algorithm:
        gen_list = [i.zfill(len(max(self.gen_list, key=len))) for i in self.gen_list]
        p = []
        out_list = []
        for i in range(len(in_bin)):  # for each bit in the sequence
            chunk = ''
            for gen in gen_list:  # for each generator given
                res = int(in_bin[i]) * int(gen[len(gen) - 1])
                for L in range(1, len(gen)):  # for each bit in the generator
                    res += int(self.reg[L - 1]) * int(gen[len(gen) - 1 - L])
                chunk += str(res % 2)
            self.reg[:] = [int(in_bin[i])] + self.reg[:len(self.reg) - 1]  # update the registers
            p.append(chunk)

        for chunk in p:
            for i in range(len(chunk)):
                out_list.append(int(chunk[i]))
        return out_list

    def decode(self, data: List[int]) -> (bytes, int):
        """
        decode data bytes. The function assumes initial and final state of encoder was at the zero state.

        :param data: coded data to be decoded, list of ints representing each received bit.
        :return: return a tuple of decoded data, and the amount of corrected errors.
        :rtype: (bytes, int)
        """
        chunk_len = len(self.gen_list)
        chunk_list = ["".join(str(data[y + x]) for y in range(chunk_len)) for x in range(0, len(data), chunk_len)]
        gen_list = [i.zfill(len(max(self.gen_list, key=len))) for i in self.gen_list]
        state = '0' * self.K
        # create a state table
        state_dict = {}
        for i in range(2 ** self.K):  # for each state
            state_dict[state] = {}
            for d in range(2):
                excepted = ''
                for gen in gen_list:
                    res = int(d * int(gen[len(gen) - 1]))
                    for L in range(1, len(gen)):
                        res += int(state[L - 1]) * int(gen[len(gen) - 1 - L])
                    excepted += str(res % 2)
                state_dict[state][d] = {'output': excepted, 'next': str(d) + state[:-1]}
            state = str(bin(int(state, 2) + 1)[2:].zfill(self.K))
        # viterbi's algorithm
        trails_list = [[['0' * self.K], 0]]     # starting point
        for i in range(len(chunk_list)):
            a = len(trails_list)
            for j in range(a):
                for k in range(2):
                    curr = trails_list[j][0][-1]
                    excepted = state_dict[curr][k]['output']
                    next_state = state_dict[curr][k]['next']
                    trail_len = sum(c1 != c2 for c1, c2 in zip(excepted, chunk_list[i]))
                    trail_len += trails_list[j][1]
                    trails_list.append([trails_list[j][0] + [next_state], trail_len])
            max_len = max(len(x[0]) for x in trails_list)
            temp_ls = []
            for ls in trails_list:
                if len(ls[0]) == max_len:
                    temp_ls.append(ls)
            trails_list = temp_ls

            if len(trails_list) == 2 ** (self.K + 1):
                state = '0' * self.K
                for n in range(2 ** self.K):
                    junction = [trails_list[x] for x in range(len(trails_list)) if trails_list[x][0][-1] == state]
                    max_len = max(x[1] for x in junction)
                    junction[:] = [x for x in junction if x[1] == max_len][0]
                    trails_list.remove(junction)
                    state = str(bin(int(state, 2) + 1)[2:].zfill(self.K))
        best_trail = [x for x in trails_list if x[0][-1] == '0'*self.K]
        min_len = min(x[1] for x in best_trail)
        best_trail = [x for x in best_trail if x[1] == min_len][0]

        decoded_word = ''
        for i in range(len(best_trail[0]) - 1):
            curr = best_trail[0][i]
            next_state = best_trail[0][i + 1]
            for mode, sub_dict in state_dict.items():
                for out, nxt in sub_dict.items():
                    if mode == curr and nxt['next'] == next_state:
                        decoded_word += str(out)
                        break

        decoded_word = decoded_word[:-self.K]
        decoded_byte = b''
        for i in range(0, len(decoded_word), 8):
            decoded_byte += bytes([int(decoded_word[i:i + 8], 2)])
        errors = best_trail[1]
        return decoded_byte, errors


if __name__ == "__main__":
    # example of constructing an encoder with constraint length = 2
    # and generators:
    #       g1(x) = 1 + x^2, represented in binary as b101 = 5
    # #       g2(x) = 1 + x+ x^2, represented in binary as b111 = 7
    conv = ConvolutionalCode((5, 7))
    #
    # # encoding a byte stream
    input_bytes = b"\xFE\xF0\x0A\x01"
    encoded = conv.encode(input_bytes)
    # print(encoded == [1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0,
    #                   0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1,
    #                   1, 1])

    # decoding a byte stream
    decoded, corrected_errors = conv.decode(encoded)
    print(decoded == input_bytes)
    print(corrected_errors)

#     # introduced five random bit flips
#     import random
#
#     corrupted = encoded.copy()
#     for _ in range(5):
#         idx = random.randint(0, len(encoded) - 1)
#         corrupted[idx] = int(not (corrupted[idx]))
#     decoded, corrected_errors = conv.decode(corrupted)
#     print(decoded == input_bytes)
#     print(corrected_errors)
#
#     # example of constructing an encoder with constraint length = 3, and rate 1/3
#     # and generators:
#     #       g1(x) = 1 + x, represented in binary as b011 = 3
#     #       g2(x) = 1 + x + x^2, represented in binary as b111 = 7
#     #       g3(x) = 1 + x^2 + x^3, represented in binary as b1101 = 13
#     conv = ConvolutionalCode((3, 7, 13))
#     #
#     # # encoding a byte stream
#     input_bytes = b"\x72\x01"
#     encoded = conv.encode(input_bytes)
#     print(encoded == [0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0,
#                       0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1])
#
#     # decoding a byte stream
#     decoded, corrected_errors = conv.decode(encoded)
#     print(decoded == input_bytes)
#     print(corrected_errors)
#
#     # introduced five random bit flips
#     import random
#
#     corrupted = encoded.copy()
#     for _ in range(5):
#         idx = random.randint(0, len(encoded) - 1)
#         corrupted[idx] = int(not (corrupted[idx]))
#     decoded, corrected_errors = conv.decode(corrupted)
#
#     print(decoded == input_bytes)
#     print(corrected_errors)
#     conv = ConvolutionalCode((5, 7))
#     input_bytes = b"\xFE\xF0\x0A\x01"
#     encoded = conv.encode(input_bytes)
#     print(encoded)
#
#     #  decoding a byte stream
#     decoded, corrected_errors = conv.decode(encoded)
#     print(decoded == input_bytes)
#     print(corrected_errors)
#
#     conv = ConvolutionalCode((4, 32, 72))
#     #
#     # # encoding a byte stream
#     input_bytes = b"\x72\x01"
#     encoded = conv.encode(input_bytes)
#     print(encoded)
#     # decoding a byte stream
#     decoded, corrected_errors = conv.decode(encoded)
#     print(decoded == input_bytes)
#     print(corrected_errors)
#
#     # introduced five random bit flips
#     import random
#
#     corrupted = encoded.copy()
#     for _ in range(5):
#         idx = random.randint(0, len(encoded) - 1)
#         corrupted[idx] = int(not (corrupted[idx]))
#     decoded, corrected_errors = conv.decode(corrupted)
#
#
# conv = ConvolutionalCode((5, 7, 27, 111, 230, 34, 52 , 66, 89, 103, 153, 255))
#
# # encoding a byte stream
# input_bytes = b"\xFE\xF0\x0A\x01"
# encoded = conv.encode(input_bytes)
# print(encoded == [1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1]
# )
#
# # decoding a byte stream
# decoded, corrected_errors = conv.decode(encoded)
# print(decoded == input_bytes)
# print(corrected_errors)
#
# # introduced five random bit flips
# import random
# corrupted = encoded.copy()
# for _ in range(30):
#     idx = random.randint(0, len(encoded) - 1)
#     corrupted[idx] = int(not (corrupted[idx]))
# decoded, corrected_errors = conv.decode(corrupted)
#
# print(decoded == input_bytes)
# print(corrected_errors)