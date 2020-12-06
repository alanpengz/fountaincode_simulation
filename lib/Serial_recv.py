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
from rs_image_lib import rs_decode_image


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

# 接收校验
def recv_check(recv_data):
    data_array = bytearray(recv_data)
    sum = int(0)
    zero = bytes(0)
    odd_flag = False

    if not len(data_array) % 2 == 0:
        odd_flag = True
        data_array.insert(len(data_array), 0)

    for i in range(0, len(data_array), 2):
        val = int.from_bytes(data_array[i:i + 2], 'big')
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


class Receiver:
    def __init__(self, port,
                 baudrate,
                 timeout,
                 ):

        self.port = serial.Serial(port, baudrate)
        # if (self.port.is_open):
        #     print("串口{}打开成功".format(self.port.portstr))
        # else:
        #     print("串口打开失败")

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
        self.wlt_ds = 0
        self.detect_done = False


    '探测序列检测部分，检测完成返回ack'
    def detect_exam(self):
        success_times = 0
        recv_id = 0
        while recv_id < 10:
            recv_bytes = self.catch_a_drop_use_serial()

            if recv_bytes is not None:
                recv_id += 1
                print('recv id:', recv_id)
                results = recv_check(recv_bytes)
                if not results == None:
                    success_times += 1
                    print('success rate:{}/{}'.format(success_times, recv_id))

        success_rate = float(success_times / 10)
        if success_rate > 0.5:
            self.detect_done = True

        self.send_detect_ack()

    def send_detect_ack(self):
        ack_good = b'ok'
        ack_bad = b'no'
        if self.detect_done:
            self.port.write(ack_good)
            self.port.flushOutput()
        else:
            self.port.write(ack_bad)
            self.port.flushOutput()
        print('send detect ack done')

    '''LT喷泉码接收解码部分'''
    def begin_to_catch(self):

        a_drop_bytes = self.catch_a_drop_use_serial()          # bytes

        if a_drop_bytes is not None:
            check_data = recv_check(a_drop_bytes)

        # if check_data is None:
        #     self.begin_to_catch()
        # else:
            if not check_data == None:
                self.drop_id += 1
                print("recv drops id : ", self.drop_id)
                self.drop_byte_size = len(check_data)
                self.add_a_drop(check_data)                                           # bytes --- drop --- bits

    data_rec =''

    def catch_a_drop_use_serial(self):
        time.sleep(1)
        size1 = self.port.in_waiting
        if size1:
            self.data_rec = self.port.read_all()
            frame_len = len(self.data_rec)
            if self.data_rec[0:2] == b'ok' and self.data_rec[frame_len - 4:frame_len] == b'fine':
                data_array = bytearray(self.data_rec)
                data_array.pop(0)
                data_array.pop(0)
                data_array.pop()
                data_array.pop()
                data_array.pop()
                data_array.pop()
                a = len(bytes(data_array))
                print('drop len(crc) :', a)

                return bytes(data_array)
            else:
                print('Wrong receive frame !')
        else:
            self.port.flushInput()

    def add_a_drop(self, d_byte):
        recv_time_start = time.time()
        drop = self.glass.droplet_from_Bytes(d_byte)           # drop

        print('drop data len: ', len(drop.data))

        if self.glass.num_chunks == 0:
            print('init num_chunks : ', drop.num_chunks)
            self.glass = Glass(drop.num_chunks)                 # 初始化接收glass
            self.chunk_size = len(drop.data)

        lt_decode_start = time.time()
        self.glass.addDroplet(drop)                             # glass add drops

        logging.info('current chunks')
        logging.info([ii if ii == None else '++++' for ii in self.glass.chunks])

        if self.glass.isDone():
            lt_decode_end = time.time()
            print('LT decode time:', lt_decode_end - lt_decode_start)

            self.recv_bit = self.glass.get_bits()                   # bits

            # a = self.recv_bit.length()
            print('recv bits length : ', int(self.recv_bit.length()))

            if (int(self.recv_bit.length()) > 0) and \
                    (self.recv_bit.length() > self.current_recv_bits_len):
                self.current_recv_bits_len = int(self.recv_bit.length())

                self.i_spiht = self._123(self.recv_bit)
                try:
                    SPIHT_time_start = time.time()
                    self.i_dwt[0] = spiht_decode(self.i_spiht[0], self.eng)
                    self.i_dwt[1] = spiht_decode(self.i_spiht[1], self.eng)
                    self.i_dwt[2] = spiht_decode(self.i_spiht[2], self.eng)
                    self.img_mat = [func_IDWT(ii) for ii in self.i_dwt]
                    SPIHT_time_end = time.time()
                    print('SPIHT decode time:', SPIHT_time_end - SPIHT_time_start)
                    print('recv time total cost:', SPIHT_time_end - recv_time_start)

                    #  单通道处理
                    #  self.idwt_coeff_r = spiht_decode(self.recv_bit, self.eng)
                    #  self.r_mat =func_IDWT(self.idwt_coeff_r)
                    self.img_shape = self.img_mat[0].shape
                    self.show_recv_img()
                    self.recv_done_flag = True
                    self.send_recv_done_ack()
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

                #  单通道处理
                #  G = self.r_mat[i, j]
                #  G = 255
                #  B = 255
                new_value = (int(R), int(G), int(B))
                self.recv_img.putpixel((i, j), new_value)
        self.recv_img.show()
        self.recv_img.save(os.path.join(self.test_dir, str(self.drop_id)) + ".bmp")

    def _123(self, bits):                          # 将rgb拆成r,g,b
        self.recv_bit_len = int(bits.length())
        i_spiht_list = []
        #  if bits % 3 == 0:
        #  print('')
        # chunk_size = self.chunk_size
        rgb_chunk_bit_size = 12000
        print('self.glass.chunk_bit_size : ', self.glass.chunk_bit_size)
        #  bits.tofile(open(str(self.drop_id), 'w'))
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

    def w1_123(self, w1_bits):  # 将rgb拆成r,g,b
        self.recv_bit_len = int(w1_bits.length())
        i_spiht_list = []
        #  if bits % 3 == 0:
        #  print('')
        # chunk_size = self.chunk_size
        rgb_chunk_bit_size = 12000
        print('self.glass.chunk_bit_size : ', self.glass.chunk_bit_size)

        each_chunk_bit_size = int(rgb_chunk_bit_size / 3)
        r_bits = bitarray.bitarray('')
        g_bits = bitarray.bitarray('')
        b_bits = bitarray.bitarray('')
        print('w1_bit len : ', w1_bits.length())

        num_rgb_chunks = int(ceil(int(w1_bits.length()) / float(rgb_chunk_bit_size)))
        rgb_bits_left = int(w1_bits.length() % rgb_chunk_bit_size)

        for i in range(num_rgb_chunks):
            start = i * rgb_chunk_bit_size
            end = min((i + 1) * rgb_chunk_bit_size, int(w1_bits.length()))
            tap_chunk = w1_bits[start: end]

            if i == num_rgb_chunks - 1 and rgb_bits_left < each_chunk_bit_size:
                r_bits += tap_chunk[each_chunk_bit_size * 0:]
                break

            elif i == num_rgb_chunks - 1 and each_chunk_bit_size < rgb_bits_left < each_chunk_bit_size * 2:
                r_bits += tap_chunk[each_chunk_bit_size * 0: each_chunk_bit_size * 1]
                g_bits += tap_chunk[each_chunk_bit_size * 1:]
                break
            elif i == num_rgb_chunks - 1 and each_chunk_bit_size * 2 < rgb_bits_left < each_chunk_bit_size * 3:
                r_bits += tap_chunk[each_chunk_bit_size * 0: each_chunk_bit_size * 1]
                g_bits += tap_chunk[each_chunk_bit_size * 1: each_chunk_bit_size * 2]
                b_bits += tap_chunk[each_chunk_bit_size * 2:]

            r_bits += tap_chunk[each_chunk_bit_size * 0: each_chunk_bit_size * 1]
            g_bits += tap_chunk[each_chunk_bit_size * 1: each_chunk_bit_size * 2]
            b_bits += tap_chunk[each_chunk_bit_size * 2:]

        rgb = list('rgb')
        #  r_bits.tofile(open("r_"+str(self.drop_id), 'w'))
        rgb_bits = [r_bits, g_bits, b_bits]
        return rgb_bits

        # self.recv_bit_len = int(bits.length())
        # i_spiht_list = []
        # #  if bits % 3 == 0:
        # #  print('')
        # # chunk_size = self.chunk_size
        # bit_chunk_size = self.glass.chunk_bit_size
        #
        # print('self.glass.chunk_bit_size : ', self.glass.chunk_bit_size)
        # #  bits.tofile(open(str(self.drop_id), 'w'))
        # each_chunk_size = int(ceil(bit_chunk_size / 3))                         ###
        # # each_chunk_size = 2500                                              ###################
        # r_bits = bitarray.bitarray('')
        # g_bits = bitarray.bitarray('')
        # b_bits = bitarray.bitarray('')
        # print('recv_bit len : ', bits.length())
        #
        # for i in range(int(ceil(int(bits.length()) / float(bit_chunk_size)))):
        #     start = i * bit_chunk_size
        #     end = min((i + 1) * bit_chunk_size, int(bits.length()))                           ###*8
        #     tap_chunk = bits[start: end]
        #     r_bits += tap_chunk[each_chunk_size * 0: each_chunk_size * 1]
        #     g_bits += tap_chunk[each_chunk_size * 1: each_chunk_size * 2]
        #     b_bits += tap_chunk[each_chunk_size * 2:]
        # rgb = list('rgb')
        # #  r_bits.tofile(open("r_"+str(self.drop_id), 'w'))
        # rgb_bits = [r_bits, g_bits, b_bits]
        # return rgb_bits

    def send_recv_done_ack(self):
        if self.recv_done_flag:
            ack = b'recv'
            self.port.write(ack)
            self.port.flushOutput()
            print('send recv_done_ack done')


    '''RS接收解码部分'''
    def catch_rs_use_serial(self):
        time.sleep(1)
        size1 = self.port.in_waiting
        if size1 == 0:
            # print('\r', 'serial port listening......', end='')
            print('serial port listening......')
            self.catch_rs_use_serial()
        elif size1:
            self.data_rec = self.port.read_all()
            data_array = bytearray(self.data_rec)
            self.port.flushInput()

            return bytes(data_array)

    def rs_recv_main(self):
        recv_time_start = time.time()
        self.recv_byte = self.catch_rs_use_serial()

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
                self.send_recv_done_ack()

            except:
                print('Decode error in matlab')


'''扩展窗喷泉码部分'''
class EW_Receiver(Receiver):
    def __init__(self, port, baudrate, timeout, recv_img=None):
        Receiver.__init__(self, port=port, baudrate=baudrate, timeout=timeout)

    def add_a_drop(self, d_byte):
        a_drop = self.glass.droplet_from_Bytes(d_byte)
        print("seed: {}\tnum_chunk : {}\tdata len: {}".format(a_drop.seed, a_drop.num_chunks, len(a_drop.data)))
        ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks)

        if self.glass.num_chunks == 0:
            self.wlt_ds = time.time()
            print('init num_chunks : ', a_drop.num_chunks)
            self.glass = Glass(a_drop.num_chunks)
            self.chunk_size = len(a_drop.data)


        self.glass.addDroplet(ew_drop)

        logging.info('current chunks')
        logging.info([ii if ii == None else '++++' for ii in self.glass.chunks])

        # 解码w1信息
        w1_size = 0.1
        if self.glass.is_w1_done(w1_size) and self.w1_done:
            print('w1_data complete!')
            w1_bits = self.glass.get_w1_bits(int(round(self.glass.num_chunks * w1_size)))
            self.w1_done = False
            if (int(w1_bits.length()) > 0) and \
                    (w1_bits.length() > self.current_recv_bits_len):
                self.current_recv_bits_len = w1_bits.length()
                self.i_spiht = self.w1_123(w1_bits)

                try:
                    self.i_dwt[0] = spiht_decode(self.i_spiht[0], self.eng)
                    self.i_dwt[1] = spiht_decode(self.i_spiht[1], self.eng)
                    self.i_dwt[2] = spiht_decode(self.i_spiht[2], self.eng)
                    self.img_mat = [func_IDWT(ii) for ii in self.i_dwt]

                    #  单通道处理
                    #  self.idwt_coeff_r = spiht_decode(self.recv_bit, self.eng)
                    #  self.r_mat =func_IDWT(self.idwt_coeff_r)
                    self.img_shape = self.img_mat[0].shape
                    self.show_recv_img()
                except:
                    print('decode error in matlab')

        # 解码全部信息
        if self.glass.isDone():                                                       # 喷泉码接收译码完成
            wlt_de = time.time()
            print('Window LT decode time used:', wlt_de - self.wlt_ds)
            self.recv_bit = self.glass.get_bits()
            #  print('recv bits length : ', int(self.recv_bit.length()))
            if (int(self.recv_bit.length()) > 0) and \
                    (self.recv_bit.length() > self.current_recv_bits_len):
                self.current_recv_bits_len = self.recv_bit.length()
                self.i_spiht = self._123(self.recv_bit)
                try:
                    spihtstart = time.time()
                    self.i_dwt[0] = spiht_decode(self.i_spiht[0], self.eng)
                    self.i_dwt[1] = spiht_decode(self.i_spiht[1], self.eng)
                    self.i_dwt[2] = spiht_decode(self.i_spiht[2], self.eng)
                    self.img_mat = [func_IDWT(ii) for ii in self.i_dwt]
                    spihtend = time.time()
                    print('SPIHT decode time:', spihtend - spihtstart)
                    #  单通道处理
                    #  self.idwt_coeff_r = spiht_decode(self.recv_bit, self.eng)
                    #  self.r_mat =func_IDWT(self.idwt_coeff_r)
                    self.img_shape = self.img_mat[0].shape
                    self.show_recv_img()
                    self.recv_done_flag = True
                    self.send_recv_done_ack()
                except:
                    print('decode error in matlab')


if __name__ == "__main__":
    # receiver = Receiver('COM7', baudrate=921600, timeout=1)
    # receiver = RS_Receiver('COM7', baudrate=921600, timeout=1)

    # while True:
    #     receiver.recv_main()
    #     if receiver.recv_done_flag:
    #         break
    receiver = EW_Receiver('COM7', baudrate=921600, timeout=1)
    os.mkdir(receiver.test_dir)

    receiver.detect_exam()
    if receiver.detect_done:
        time.sleep(5)
        while True:
            receiver.rs_recv_main()
            if receiver.recv_done_flag:
                print('RS-SPIHT receive done!')
                break

    else:
        time.sleep(5)
        while True:
            receiver.begin_to_catch()
            if receiver.glass.isDone():
                print('LT-SPIHT receive done!')
                break
