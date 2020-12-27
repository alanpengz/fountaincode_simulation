# _*_ coding=utf-8 _*_ 
from __future__ import print_function


from unireedsolomon import rs
from math import ceil, log
import numpy as np
import struct, bitarray
import six
import os
import matplotlib.pyplot as plt
from PIL import Image

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
SIM_PATH = os.path.join(LIB_PATH, '../simulation')
PRO_PATH = os.path.join(SIM_PATH, 'processing')

RS_FILE = "timg.jpg.rs"
RE_CONTRUCT_IMAGE = "timg_recontruct.jpg"
PACKET_SIZE = 1000

WHALE_128_JPG = os.path.join(DOC_PATH, "whale_128.jpg")
LENA_IMG = os.path.join(DOC_PATH, 'lena.png')



def n_k_s_to_image(image_data, packet_size):

    s = packet_size
    k = int(ceil((len(image_data) + 8) / float(packet_size)))
    n = int(2 ** ceil(log(k) / log(2)) - 1)
    print(n, k, packet_size)

    bits_n = format(n, "016b")
    bits_k = format(k, "016b")
    bits_s = format(packet_size, "032b")
    byte_n = bitarray.bitarray(bits_n).tobytes()
    byte_k = bitarray.bitarray(bits_k).tobytes()
    byte_s = bitarray.bitarray(bits_s).tobytes()
   
    image_contain = byte_n + byte_k + byte_s + image_data
    return n, k, packet_size, image_contain


def n_k_s_from_image(rs_bytes):

    n_bytes = rs_bytes[0:2]
    k_bytes = rs_bytes[2:4]
    s_bytes = rs_bytes[4:8]
    image_contain = rs_bytes[8:]

    byte_factory = bitarray.bitarray(endian='big')
    byte_factory.frombytes(n_bytes)
    n_bits = byte_factory.to01()
    n = int(n_bits, base=2)

    byte_factory = bitarray.bitarray(endian='big')
    byte_factory.frombytes(k_bytes)
    k_bits = byte_factory.to01()
    k = int(k_bits, base=2)

    byte_factory = bitarray.bitarray(endian='big')
    byte_factory.frombytes(s_bytes)
    s_bits = byte_factory.to01()
    s = int(s_bits, base=2)

    return n, k, s, image_contain


def rs_encode_image(image_data, packet_size):
    '''
    读取文件，按 packet_size大小划分为待编码块
    按行排列，
    按纵向进行RS编码，增加冗余的编码数据块

                  packet_size 
    -------------------------------------------
    | |              图像文件                 |
RS  -------------------------------------------
    | |              图像文件                 |
    -------------------------------------------
编  | |              图像文件                 |
    -------------------------------------------
    | |              图像文件                 |
码  -------------------------------------------
    | |              图像文件                 |
    -------------------------------------------
块  |*|**************冗余编码*****************|
    -------------------------------------------
    |*|**************冗余编码*****************|
    -------------------------------------------

    '''
    n, k, s, image_contain = n_k_s_to_image(image_data, packet_size)
    print(k, n)
    mat = []
    for i in range(k):
        if(len(image_contain) > (i+1) * packet_size):
            if six.PY3:
                mat_temp = list(image_contain[i * packet_size: (i+1) * packet_size])
            else:
                mat_temp = [ord(ii) for ii in list(image_contain[i * packet_size: (i+1) * packet_size])]
            mat.append(mat_temp)
        else:                                                         # 处理最后一个packet
            empty = [0 for ii in range(packet_size)]
            if six.PY3:
                empty[:(len(image_contain) - i * packet_size)] = \
                    list(image_contain[i * packet_size: len(image_contain)])
            else:
                empty[:(len(image_contain) - i * packet_size)] = \
                    [ord(ii) for ii in list(image_contain[i * packet_size: len(image_contain)])]
            mat.append(empty)                                                # mat[] = [, , , , ]

    for i in range(n-k):
        mat.append([0 for ii in range(packet_size)])

    mat_arr_orig = np.array(mat)
    mat_arr_code = mat_arr_orig

    coder = rs.RSCoder(n, k)

    for i in range(packet_size):
        source = ''.join([chr(ii) for ii in mat_arr_orig[:k, i]])                # str
        code_word = list(coder.encode(source))                                  # string list
        mat_arr_code[:, i] = [ord(ii) for ii in code_word]                                       # 按列进行编码

    out_image_contain = b''
    for line in mat_arr_code:                                                                   # 按行输出
        if six.PY3:
            out_bytes = b''.join([struct.pack("B", ii) for ii in list(line)])
        elif six.PY2:
            out_bytes = b''.join([struct.pack("B", int(ii)) for ii in list(line)])

        out_image_contain += out_bytes
    return out_image_contain


def rs_decode_image(rs_data):
    n, k, s, rs_contain = n_k_s_from_image(rs_data)
    packet_size = int(s)

    mat = []
    for i in range(n):
        if(len(rs_contain) >= (i+1) * packet_size):
            if six.PY3:
                mat_temp = list(rs_contain[i * packet_size: (i+1) * packet_size])
            else:
                mat_temp = [ord(ii) for ii in list(rs_contain[i * packet_size: (i+1) * packet_size])]
            mat.append(mat_temp)
        else:
            empty = [0 for ii in range(packet_size)]
            if len(rs_contain) > (i+1) * packet_size:
                if six.PY3:
                    empty[:(len(rs_contain) - i * packet_size)] = \
                            list(rs_contain[i * packet_size: len(rs_contain)])
                else:
                    empty[:(len(rs_contain) - i * packet_size)] = \
                            [ord(ii) for ii in list(rs_contain[i * packet_size: len(rs_contain)])]

            mat.append(empty)
    mat_arr_code = np.array(mat)            
    mat_arr_orig = mat_arr_code[:k, :]

    coder = rs.RSCoder(n, k)
    for i in range(packet_size):
        code_word = b''.join(struct.pack("B", ii) for ii in mat_arr_code[:, i]) # bytes
        source = coder.decode(code_word)[0] # list str
        source = [ii for ii in source]
        if len(source) < k:
            mat_arr_orig[0:(k-len(source)), i] = [0 for ii in range(k-len(source))]
            mat_arr_orig[(k-len(source)):, i] = [ord(ii) for ii in source]
        else:
            mat_arr_orig[:, i] = [ord(ii) for ii in source]
    
    out_image_contain = b''

    for line in mat_arr_orig[:, :]:
        out_bytes = b''.join([struct.pack("B", ii) for ii in list(line)])
        out_image_contain += out_bytes

    print('RS decode done!')

    return out_image_contain


if __name__ == "__main__":
    # img = FISH_128_JGP
    img = LENA_IMG
    print(rs_encode_image(img, PACKET_SIZE))
    print(rs_decode_image(img +".rs"))

    # n_k_s_to_image(img, PACKET_SIZE)

