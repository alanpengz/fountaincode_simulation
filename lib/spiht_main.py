import matlab.engine
import os
import struct
import bitarray
import numpy as np

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
LEAN_IMG = os.path.join(DOC_PATH, 'lena512.bmp')
OUT_BIN = os.path.join(DOC_PATH, 'out.bin')
LEAN_IMG_NEW = os.path.join(DOC_PATH, 'lena512_reconstruct.bmp')
LEVEL=9

def spiht_encode():
    eng = matlab.engine.start_matlab()
    eng.addpath(LIB_PATH)
    img_enc = eng.func_SPIHT_Encode(LEAN_IMG)
    print (len(img_enc[0]))
    return img_enc

def code_to_file():
    img_enc = spiht_encode()[0]
    bitstream = ''
    info_array = []
    for i in img_enc:
        if i == 0 or i == 1:
            bitstream += str(i).replace('.0', '')
        elif i == 2:
            pass
        else:
            print (i)
            #  info_array.append(i)
            #  bitstream += (bin(int(i)).replace('0b', '') + ',')
    fout = open(OUT_BIN, 'wb')
    bits = bitarray.bitarray(bitstream)
    bits.tofile(fout)
    fout.close()
    print (len(bitstream) )
    return bitstream

def file_to_code():
    fin = open(OUT_BIN, 'rb')
    read_bits = bitarray.bitarray()
    read_bits.fromfile(fin)
    fin.close()
    #  print (read_bits)
    return read_bits


def spiht_decode():
    img_code = [512.0, 15.0, float(LEVEL)]
    img_code.extend(list(file_to_code())[:-1])
    img_code = matlab.mlarray.double(img_code)
    S = [1]
    for i in range(10):
        S.append(2 ** i)
    S = [S, S]
    S.append([ii * ii for ii in S[0]])
    S = matlab.double([list(ii) for ii in np.array(S).transpose()])

    eng = matlab.engine.start_matlab()
    eng.addpath(LIB_PATH)
    S = eng.func_SPIHT_Decode(S, img_code, LEAN_IMG_NEW, LEAN_IMG)
    return S

def test_main():
    eng = matlab.engine.start_matlab()
    eng.addpath(LIB_PATH)
    S = eng.func_SPIHT_Encode(LEAN_IMG)
    return S


if __name__ == '__main__':
    #  img_enc = spiht_encode()
    bitstream = code_to_file()
    #  read_bits = file_to_code()
    #  spiht_decode()
    #  S = test_main()
    S = spiht_decode()


