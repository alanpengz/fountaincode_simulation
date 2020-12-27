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
from rs_image_lib import rs_encode_image


LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
LENA_IMG = os.path.join(DOC_PATH, 'lena.jpg')
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

# 添加校验和、帧头
def send_check(send_bytes):
    data_array = bytearray(send_bytes)
    sum = int(0)
    zero = bytes(0)

    frame_start = b'ok'
    frame_end = b'fine'

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

    get_reverse = 65535 - sum
    check_sum = get_reverse.to_bytes(2, 'big')

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


class Sender:
    def __init__(self, port,
                 baudrate,
                 timeout,
                 img_path=LENA_IMG,
                 level=3,
                 wavelet='bior4.4',
                 mode='periodization',

                 fountain_chunk_size=200,          # 应能被数据长度30000整除
                 fountain_type='normal',
                 drop_interval=1,

                 w1_size=0.1,
                 w1_pro=0.084,
                 seed=None):

        # self.port = serial.Serial(port, baudrate)
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
        self.recvdone_ack = False
        self.detect_ack = False
        self.rs_send = False
        self.lt_send = False
        self.detect_start_time = 0

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
            print("++++++++++++++++++++", len(img.tobytes()))
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

        self.fountain = self.fountain_builder()

        #  a = [os.remove(ii) for ii in temp_file_list]
        self.show_info()
        # self.a_drop()

    def fountain_builder(self):
        if self.fountain_type == 'normal':
            return Fountain(self.m, chunk_size=self.fountain_chunk_size, seed=self.seed)
        elif self.fountain_type == 'ew':
            return EW_Fountain(self.m,
                               chunk_size=self.fountain_chunk_size,
                               w1_size=self.w1_p,
                               w1_pro=self.w1_pro,
                               seed=self.seed)

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
        print('rgb bitstream len:', len(m_list))
        print('data bytes should be:', len(m_list)/8)

        for i in range(int(ceil(len(m_list[0]) / float(each_chunk_bit_size)))):     #
            start = i * each_chunk_bit_size
            end = min((i + 1) * each_chunk_bit_size, len(m_list[0]))

            m_bytes += m_list[0][start: end].tobytes()
            m_bytes += m_list[1][start: end].tobytes()
            m_bytes += m_list[2][start: end].tobytes()

        print('compose_rgb len(m):', len(m_bytes))  # r,g,b(size)+...+

        return m_bytes, each_chunk_bit_size * 3
    # def compose_rgb(self, file_list, each_chunk_bit_size=2500):
    #     '''
    #     将三个文件和并为一个文件
    #     '''
    #     m_list = []
    #     m_list.append(file_to_code(file_list[0]))  # 不用file_to_code()                             bitaray
    #     m_list.append(file_to_code(file_list[1]))
    #     m_list.append(file_to_code(file_list[2]))
    #
    #     # bitarray.bitarray.tostring(file_to_code(file_list[0]))
    #     # bitarray.bitarray.tostring(file_to_code(file_list[0]))
    #     # bitarray.bitarray.tostring(file_to_code(file_list[0]))
    #     # m_list.append(open(file_list[0], encoding='utf-8', errors='ignore').read())                # 不用file_to_code()
    #     # m_list.append(open(file_list[1], encoding='utf-8', errors='ignore').read())
    #     # m_list.append(open(file_list[2], encoding='utf-8', errors='ignore').read())                  # [str, str, str]
    #     # m_list.append(open(file_list[0], 'rb').read())
    #     # m_list.append(open(file_list[1], 'rb').read())
    #     # m_list.append(open(file_list[2], 'rb').read())
    #     #  a = [print(len(ii)) for ii in m_list]
    #     m = ''
    #     print(len(m_list[0]))
    #     print(len(m_list[1]))
    #     print(len(m_list[2]))
    #     for i in range(int(ceil(len(m_list[0]) / float(each_chunk_bit_size)))):
    #         start = i * each_chunk_bit_size
    #         end = min((i + 1) * each_chunk_bit_size, len(m_list[0]))
    #         #  m += ''.join([ii[start:end] for ii in m_list])
    #         m += ''.join(bitarray2str(m_list[0][start: end]))
    #         m += ''.join(bitarray2str(m_list[1][start: end]))
    #         m += ''.join(bitarray2str(m_list[2][start: end]))
    #
    #     print('compose_rgb len(m):', len(m))  # r,g,b(size)+...+
    #     # with open(SEND_PATH, "w", encoding='utf-8') as f:
    #     #     f.write(m)
    #     return m, each_chunk_bit_size * 3



    # def compose_rgb(self, file_list, each_chunk_size=2500):
    #     '''
    #     将三个文件和并为一个文件
    #     '''
    #     m_list = []
    #     m_list.append(file_to_code(file_list[0]))  # 不用file_to_code()                             bitaray
    #     m_list.append(file_to_code(file_list[1]))
    #     m_list.append(file_to_code(file_list[2]))
    #
    #     # bitarray.bitarray.tostring(file_to_code(file_list[0]))
    #     # bitarray.bitarray.tostring(file_to_code(file_list[0]))
    #     # bitarray.bitarray.tostring(file_to_code(file_list[0]))
    #     # m_list.append(open(file_list[0], encoding='utf-8', errors='ignore').read())                # 不用file_to_code()
    #     # m_list.append(open(file_list[1], encoding='utf-8', errors='ignore').read())
    #     # m_list.append(open(file_list[2], encoding='utf-8', errors='ignore').read())                  # [str, str, str]
    #     # m_list.append(open(file_list[0], 'rb').read())
    #     # m_list.append(open(file_list[1], 'rb').read())
    #     # m_list.append(open(file_list[2], 'rb').read())
    #     #  a = [print(len(ii)) for ii in m_list]
    #     m = ''
    #     print(len(m_list[0]))
    #     print(len(m_list[1]))
    #     print(len(m_list[2]))
    #     for i in range(int(ceil(len(m_list[0]) / float(each_chunk_size)))):
    #         start = i * each_chunk_size
    #         end = min((i + 1) * each_chunk_size, len(m_list[0]))
    #         #  m += ''.join([ii[start:end] for ii in m_list])
    #         m += ''.join(m_list[0][start: end])
    #         m += ''.join(m_list[1][start: end])
    #         m += ''.join(m_list[2][start: end])
    #
    #     print('compose_rgb len(m):', len(m))                                       # r,g,b(size)+...+
    #     # with open(SEND_PATH, "w", encoding='utf-8') as f:
    #     #     f.write(m)
    #     return m, each_chunk_size * 3


    def show_info(self):
        self.fountain.show_info()

    def a_drop(self):
        a = self.fountain.droplet().toBytes()
        # with open(SEND_PATH, "w", encoding='utf-8') as f:
        #     f.write(str(a))
        return a


    '''发送探测序列部分，根据探测序列接收端反馈决定RS-SPIHT图像直传or喷泉码'''
    def send_detect_sequence(self):
        detect_start_time = time.time()
        print('Start sending detect sequence......')
        detect_sequence = b'this_is_a_detect_sequence'
        send_times = 1
        while True:
            time.sleep(1)
            self.port.write(send_check(detect_sequence))
            self.port.flushOutput()
            print('detect sequence send times:', send_times)
            send_times += 1
            self.ack_detect()
            time_now = time.time()
            time_used = time_now - detect_start_time
            if self.detect_ack:
                break
            elif time_used > 60:        # 接收ack超时中断，使用喷泉码
                self.lt_send = True
                break

    def ack_detect(self):           # 探测序列ack检测
        time.sleep(1)
        size1 = self.port.in_waiting
        if size1 == 2:
            data_rec = self.port.read_all()
            data_array = bytearray(data_rec)
            if data_array[:] == b'ok':
                self.detect_ack = True
                self.rs_send = True
            elif data_array[:] == b'no':
                self.detect_ack = True
                self.lt_send = True


    '''使用LT喷泉码发送方式'''
    def send_drops_use_serial(self):
        #     send_data = a_drop.encode('utf-8')
        #     self.port.write(send_data)
        packet_discard_rate = 0.1
        discard_one = int(1 / packet_discard_rate)
        while True:
            time.sleep(self.drop_interval)
            self.drop_id += 1

            # a = len(self.a_drop()
            if self.drop_id % discard_one == 0:
                print("Discard one")
                # self.a_drop()
            else:

                print('drop id : ', self.drop_id)
                print("send_drops_len:{}".format(len(self.a_drop())))
                self.port.write(send_check(self.a_drop()))
                self.port.flushOutput()
            self.recvdone_ack_detect()
            if self.recvdone_ack:
                break

    def recvdone_ack_detect(self):          # '''接收是否完成的ack检测'''
        time.sleep(1)
        size1 = self.port.in_waiting
        if size1 == 4:
            data_rec = self.port.read_all()
            data_array = bytearray(data_rec)
            if data_array[:] == b'recv':
                self.recvdone_ack = True


    '''RS-SPIHT发送部分'''
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
            self.recvdone_ack_detect()
            if self.recvdone_ack:
                break





class EW_Sender(Sender):
    def __init__(self, port, baudrate, timeout, img_path=LENA_IMG, fountain_chunk_size=300, seed=None):
        Sender.__init__(self, port=port, baudrate=baudrate, timeout=timeout, img_path=img_path, fountain_chunk_size=fountain_chunk_size, fountain_type='ew', seed=seed)


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
        # os.mkdir(self.test_dir)


        # while True:
        #     self.begin_to_catch()
        #     if self.glass.isDone():
        #
        #         print('recv done')
        #         break

    def begin_to_catch(self):
        a_drop = self.catch_a_drop_use_serial()
        if not a_drop == None:
            self.drop_id += 1
            print("drops id : ", self.drop_id)
            self.drop_byte_size = len(a_drop)
            self.add_a_drop(a_drop)

    data_rec =''

    def catch_a_drop_use_serial(self):
        # size = self.port.in_waiting
        # if size:
        self.data_rec = self.port.read()
        a = len(self.data_rec)
        return self.data_rec

    def add_a_drop(self, d_byte):
        drop = self.glass.droplet_from_Bytes(d_byte)

        if self.glass.num_chunks == 0:
            print('init num_chunks : ', drop.num_chunks)
            self.glass = Glass(drop.num_chunks)
            self.chunk_size = len(drop.data)

        self.glass.addDroplet(drop)

        self.recv_bit = self.glass.get_bits()
        #  print('recv bits length : ', int(self.recv_bit.length()))
        if (int(self.recv_bit.length()) > 0) and \
                (self.recv_bit.length() > self.current_recv_bits_len):
            self.current_recv_bits_len = int(self.recv_bit.length())
            #  self.recv_bit.tofile(open('./recv_tmp.txt', 'w'))
            self.i_spiht = self._123(self.recv_bit, self.chunk_size)
            #  self.i_dwt = [spiht_decode(ii, self.eng) for ii in self.i_spiht]
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

    def _123(self, bits, chunk_size):                          # 将rgb拆成r,g,b
        self.recv_bit_len = int(bits.length())
        i_spiht_list = []
        #  if bits % 3 == 0:
        #  print('')
        # chunk_size = self.chunk_size
        chunk_size = self.glass.chunk_bit_size
        print('self.glass.chunk_bit_size : ', self.glass.chunk_bit_size)
        #  bits.tofile(open(str(self.drop_id), 'w'))
        each_chunk_size = chunk_size / 3
        r_bits = bitarray.bitarray('')
        g_bits = bitarray.bitarray('')
        b_bits = bitarray.bitarray('')
        print('recv_bit len : ', bits.length())

        for i in range(int(ceil(int(bits.length()) / float(chunk_size)))):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, int(bits.length())) * 8
            tap_chunk = bits[start: end]
            r_bits += tap_chunk[each_chunk_size * 0: each_chunk_size * 1]
            g_bits += tap_chunk[each_chunk_size * 1: each_chunk_size * 2]
            b_bits += tap_chunk[each_chunk_size * 2: each_chunk_size * 3]
        rgb = list('rgb')
        #  r_bits.tofile(open("r_"+str(self.drop_id), 'w'))
        rgb_bits = [r_bits, g_bits, b_bits]
        return rgb_bits


class EW_Receiver(Receiver):
    def __init__(self, recv_img=None):
        Receiver.__init__(self)

    def add_a_drop(self, d_byte):
        a_drop = self.glass.droplet_from_Bytes(d_byte)
        print("++ seed: {}\tnum_chunk : {}\tdata len: {}+++++".format(a_drop.seed, a_drop.num_chunks, len(a_drop.data)))
        ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks)

        if self.glass.num_chunks == 0:
            print('init num_chunks : ', a_drop.num_chunks)
            self.glass = Glass(a_drop.num_chunks)
            self.chunk_size = len(a_drop.data)

        self.glass.addDroplet(ew_drop)
        self.recv_bit = self.glass.get_bits()
        #  print('recv bits length : ', int(self.recv_bit.length()))
        if (int(self.recv_bit.length()) > 0) and \
                (self.recv_bit.length() > self.current_recv_bits_len):
            self.current_recv_bits_len = self.recv_bit.length()
            self.i_spiht = self._123(self.recv_bit, self.chunk_size)
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


if __name__ == "__main__":
    print("starting")
    sender = Sender('COM6', baudrate=921600, timeout=1)
    # sender = RS_Sender('COM6', baudrate=921600, timeout=1)
    # sender.send_rs_use_serial()
    # sender = EW_Sender('COM6', baudrate=921600, timeout=1)
    # sender.send_detect_sequence()
    # if sender.rs_send:
    #     sender.send_rs_use_serial()

    # elif sender.lt_send:
    #     sender.send_drops_use_serial()

    # else:
    #     sender.send_drops_use_serial()



