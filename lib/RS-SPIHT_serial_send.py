# _*_ coding=utf-8 _*_
from __future__ import print_function


import sys, os
import numpy as np
from math import ceil
import pywt
import bitarray
import matlab.engine
from PIL import Image
import time, serial

sys.path.append('.')
from dwt_lib import load_img
from fountain_lib import Fountain, Glass
from fountain_lib import EW_Fountain, EW_Droplet
from spiht_dwt_lib import spiht_encode, func_DWT, code_to_file, spiht_decode, func_IDWT, file_to_code
from rs_image_lib import rs_encode_image, rs_decode_image

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
LENA_IMG = os.path.join(DOC_PATH, 'lena.png')
GAKKI_PATH = os.path.join(DOC_PATH, 'gakki128.png')
TEST_PATH = os.path.join(DOC_PATH, 'test')
SIM_PATH = os.path.join(LIB_PATH, '../simulation')
WHALE_IMG = os.path.join(DOC_PATH, 'whale.bmp')
TEST_PIX = os.path.join(DOC_PATH, 'testpix.png')
WHALE_IMG_128 = os.path.join(DOC_PATH, 'whale_128.png')
SEND_PATH = os.path.join(DOC_PATH, 'sendbytes.txt')
RECV_PATH = os.path.join(DOC_PATH, 'recvbytes.txt')

def bitarray2str(bit):
    return bit.tobytes()


def send_check(send_bytes):
    data_array = bytearray(send_bytes)
    sum = int(0)
    zero = bytes(0)

    frame_start = b'ok'
    frame_end = b'fuck'

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

    get_reverse = 65535 - sum
    check_sum = get_reverse.to_bytes(2, 'little')

    data_array.insert(0, check_sum[0])
    data_array.insert(1, check_sum[1])
    data_array.insert(0, frame_start[0])
    data_array.insert(1, frame_start[1])

    if odd_flag:
        data_array.pop()

    data_array.insert(len(data_array), frame_end[0])
    data_array.insert(len(data_array), frame_end[1])
    data_array.insert(len(data_array), frame_end[2])
    data_array.insert(len(data_array), frame_end[3])

    return bytes(data_array)


def bits2string(b):
    return ''.join(chr(int(''.join(x), 2)) for x in zip(*[iter(b)]*8))


BIOR = 'bior4.4'           # 小波基
MODE = 'periodization'
LEVEL = 3


class RS_Sender:
    def __init__(self, port,
                 baudrate,
                 timeout,
                 img_path=LENA_IMG,
                 level=3,
                 wavelet='bior4.4',
                 mode='periodization',

                 fountain_chunk_size=3000,          # 应能被数据长度30000整除
                 fountain_type='normal',
                 drop_interval=1,

                 w1_size=0.1,
                 w1_pro=0.084,
                 seed=None):

        self.port = serial.Serial(port, baudrate)
        self.drop_id = 0
        self.eng = matlab.engine.start_matlab()
        self.eng.addpath(LIB_PATH)
        self.img_path = img_path
        self.fountain_chunk_size = fountain_chunk_size
        self.fountain_type = fountain_type
        self.drop_interval = drop_interval
        self.w1_p = w1_size
        self.w1_pro = w1_pro
        # self.port = port
        self.seed = seed
        self.ack = False

        # if self.port.is_open:
        #     print("串口{}打开成功".format(self.port.portstr))
        # else:
        #     print("串口打开失败")

        temp_file = self.img_path  # .replace(self.img_path.split('/')[-1], 'tmp')
        rgb_list = ['r', 'g', 'b']
        temp_file_list = [temp_file + '_' + ii for ii in rgb_list]
        if self.is_need_img_process():
            print('processing image: {:s}'.format(self.img_path))
            img = load_img(self.img_path)
            (width, height) = img.size
            mat_r = np.empty((width, height))
            mat_g = np.empty((width, height))
            mat_b = np.empty((width, height))
            for i in range(width):
                for j in range(height):
                    [r, g, b] = img.getpixel((i, j))
                    mat_r[i, j] = r
                    mat_g[i, j] = g
                    mat_b[i, j] = b
            self.img_mat = [mat_r, mat_g, mat_b]
            self.dwt_coeff = [func_DWT(ii) for ii in self.img_mat]                         # r,g,b小波变换得到系数
            self.spiht_bits = [spiht_encode(ii, self.eng) for ii in self.dwt_coeff]        # r,g,b的spiht编码

            a = [code_to_file(self.spiht_bits[ii],
                              temp_file_list[ii],
                              add_to=self.fountain_chunk_size / 3 * 8)
                 for ii in range(len(rgb_list))]
        else:
            print('temp file found : {:s}'.format(self.img_path))

        self.m, _chunk_size = self.compose_rgb(temp_file_list)


    def is_need_img_process(self):                       # 判断有没有rgb文件
        #  print(sys._getframe().f_code.co_name)

        doc_list = os.listdir(os.path.dirname(self.img_path))
        img_name = self.img_path.split('/')[-1]
        suffix = ['_' + ii for ii in list('rbg')]
        target = [img_name + ii for ii in suffix]
        count = 0
        for t in target:
            if t in doc_list:
                count += 1
        if count == 3:
            return False
        else:
            return True

    def compose_rgb(self, file_list, each_chunk_bit_size=4000):                          # each_chunk_bit_size=2500, len(m_byte)不等于240000/8=30000
        '''                                                                             # each_chunk_bit_size=4000，m_byte=30000，fountain_chunk_size设置成能被30000整除，每个块长度一样，方便异或
        将三个文件和并为一个文件
        '''
        m_list = []
        m_list.append(file_to_code(file_list[0]))  # 不用file_to_code()                             bitaray
        m_list.append(file_to_code(file_list[1]))
        m_list.append(file_to_code(file_list[2]))

        m_bytes = b''
        print('r bitstream len:', len(m_list[0]))
        print('g bitstream len:', len(m_list[1]))
        print('b bitstream len:', len(m_list[2]))
        len_mlist = len(m_list[0]) + len(m_list[1]) + len(m_list[2])
        print('rgb bitstream len:', len_mlist)
        print('data bytes should be:', len_mlist/8)

        for i in range(int(ceil(len(m_list[0]) / float(each_chunk_bit_size)))):     #
            start = i * each_chunk_bit_size
            end = min((i + 1) * each_chunk_bit_size, len(m_list[0]))

            m_bytes += m_list[0][start: end].tobytes()
            m_bytes += m_list[1][start: end].tobytes()
            m_bytes += m_list[2][start: end].tobytes()

        print('compose_rgb len(m):', len(m_bytes))  # r,g,b(size)+...+

        return m_bytes, each_chunk_bit_size * 3

    def send_rs_use_serial(self):
        send_times = 1
        while True:
            time.sleep(3)
            rs_data = rs_encode_image(self.m, 500)
            print('RS coded data bytes len:', len(rs_data))
            self.port.write(rs_data)
            self.port.flushOutput()
            print('send times:', send_times)
            send_times = send_times + 1
            self.ack_detect()
            if self.ack:
                break

    def send_use_serial_one_time(self):
        time.sleep(1)
        self.port.write(self.m)
        self.port.flushOutput()
        print('send done')

    def ack_detect(self):
        time.sleep(1)
        size1 = self.port.in_waiting
        if size1 == 2:
            data_rec = self.port.read_all()
            data_array = bytearray(data_rec)
            if data_array[:] == b'ok':
                self.ack = True





if __name__ == "__main__":
    print("starting")
    sender = RS_Sender('COM6', baudrate=921600, timeout=1)
    sender.send_rs_use_serial()
