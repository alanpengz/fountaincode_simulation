# _*_ coding=utf-8 _*_
from __future__ import print_function


import sys, os
import numpy as np
from math import ceil
from math import floor

import pywt
import bitarray
import matlab.engine
from PIL import Image
import time, serial
import logging

sys.path.append('.')
from dwt_lib import load_img
from fountain_lib import Fountain, Glass
from fountain_lib import EW_Fountain, EW_Droplet
from spiht_dwt_lib import spiht_encode, func_DWT, code_to_file, spiht_decode, func_IDWT
from rs_image_lib import rs_encode_image, rs_decode_image

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
LENA_IMG = os.path.join(DOC_PATH, 'lena.png')
TEST_PATH = os.path.join(DOC_PATH, 'test')
SIM_PATH = os.path.join(LIB_PATH, '../simulation')
WHALE_IMG = os.path.join(DOC_PATH, 'whale.bmp')


BIOR = 'bior4.4'           # 小波基
MODE = 'periodization'
LEVEL = 3


def bitarray2str(bit):
    return bit.tobytes().decode('utf-8')


def recv_check(recv_data):
    data_array = bytearray(recv_data)
    sum = int(0)
    zero = bytes(0)
    odd_flag = False

    if not len(data_array) % 2 == 0:
        odd_flag = True
        data_array.insert(len(data_array), 0)

    for i in range(0, len(data_array), 2):
        val = int.from_bytes(data_array[i:i + 2], 'little')
        sum = sum + val
        sum = sum & 0xffffffff

    sum = (sum >> 16) + (sum & 0xffff)
    while sum > 65535:
        sum = (sum >> 16) + (sum & 0xffff)
    print('checksum:', sum)

    if sum == 65535:
        if odd_flag:
            data_array.pop()
            data_array.pop(0)
            data_array.pop(0)
        else:
            data_array.pop(0)
            data_array.pop(0)
        return bytes(data_array)
    else:
        print('Receive check wrong!')


class RS_Receiver:
    def __init__(self, port,
                 baudrate,
                 timeout,
                 ):

        self.port = serial.Serial(port, baudrate)
        self.eng = matlab.engine.start_matlab()
        self.eng.addpath(LIB_PATH)

        self.drop_id = 0
        self.glass = Glass(0)
        self.chunk_size = 0
        self.current_recv_bits_len = 0
        self.i_spiht = []
        self.i_dwt = [[], [], []]
        self.img_mat = []
        #  暂时
        self.idwt_coeff_r = None
        self.r_mat = None
        self.img_shape = [0, 0]
        self.recv_img = None
        self.drop_byte_size = 99999
        self.test_dir = os.path.join(TEST_PATH, time.asctime().replace(' ', '_').replace(':', '_'))
        self.w1_done = True
        self.recv_done_flag = False


    data_rec =''

    def catch_use_serial(self):
        time.sleep(1)
        size1 = self.port.in_waiting
        if size1 == 0:
            # print('\r', 'serial port listening......', end='')
            print('serial port listening......')
            self.catch_use_serial()
        elif size1:
            self.data_rec = self.port.read_all()
            data_array = bytearray(self.data_rec)
            self.port.flushInput()

            return bytes(data_array)

    def rs_recv_main(self):
        recv_time_start = time.time()
        self.recv_byte = self.catch_use_serial()

        if self.recv_byte is not None:
            rs_decode_start = time.time()
            rs_decoded = rs_decode_image(self.recv_byte)
            rs_decode_end = time.time()
            print('RS decode time:', rs_decode_end - rs_decode_start)
            bitarray_factory = bitarray.bitarray(endian='big')
            bitarray_factory.frombytes(rs_decoded)

            # if bitarray_factory is not None:
            # test = int(ceil(len(bitarray_factory) / 5))
            self.i_spiht = self._123(bitarray_factory)
            try:
                SPIHT_time_start = time.time()
                self.i_dwt[0] = spiht_decode(self.i_spiht[0], self.eng)
                self.i_dwt[1] = spiht_decode(self.i_spiht[1], self.eng)
                self.i_dwt[2] = spiht_decode(self.i_spiht[2], self.eng)
                self.img_mat = [func_IDWT(ii) for ii in self.i_dwt]
                SPIHT_time_end = time.time()
                print('SPIHT decode time:', SPIHT_time_end - SPIHT_time_start)
                self.img_shape = self.img_mat[0].shape
                self.show_recv_img()

                self.recv_done_flag = True
                recv_time_end = time.time()
                print('recv time total cost:', recv_time_end - recv_time_start)
                self.send_ack()

            except:
                print('Decode error in matlab')

    def show_recv_img(self):
        if self.recv_img == None:
            self.recv_img = Image.new('RGB', (self.img_shape[0], self.img_shape[0]), (0, 0, 20))
        for i in range(self.img_shape[0]):
            for j in range(self.img_shape[0]):
                R = self.img_mat[0][i, j]
                G = self.img_mat[1][i, j]
                B = self.img_mat[2][i, j]

                new_value = (int(R), int(G), int(B))
                self.recv_img.putpixel((i, j), new_value)
        self.recv_img.show()
        self.recv_img.save(os.path.join(self.test_dir, str(self.drop_id)) + ".bmp")

    def _123(self, bits):                          # 将rgb拆成r,g,b
        self.recv_bit_len = int(bits.length())
        rgb_chunk_bit_size = 12000
        each_chunk_size = int(rgb_chunk_bit_size / 3)
        r_bits = bitarray.bitarray('')
        g_bits = bitarray.bitarray('')
        b_bits = bitarray.bitarray('')
        print('recv_bit len : ', bits.length())

        for i in range(int(ceil(int(bits.length()) / float(rgb_chunk_bit_size)))):
            start = i * rgb_chunk_bit_size
            end = min((i + 1) * rgb_chunk_bit_size, int(bits.length()))
            tap_chunk = bits[start: end]
            r_bits += tap_chunk[each_chunk_size * 0: each_chunk_size * 1]
            g_bits += tap_chunk[each_chunk_size * 1: each_chunk_size * 2]
            b_bits += tap_chunk[each_chunk_size * 2:]
        rgb = list('rgb')
        #  r_bits.tofile(open("r_"+str(self.drop_id), 'w'))
        rgb_bits = [r_bits, g_bits, b_bits]
        return rgb_bits

    def send_ack(self):
        if self.recv_done_flag:
            ack = b'ok'
            self.port.write(ack)
            self.port.flushOutput()
            print('send ack done')


if __name__ == "__main__":
    receiver = RS_Receiver('COM7', baudrate=921600, timeout=1)
    os.mkdir(receiver.test_dir)
    while True:
        receiver.rs_recv_main()
        if receiver.recv_done_flag:
            break

