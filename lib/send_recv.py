# _*_ coding=utf-8 _*_ 
from __future__ import print_function
import sys, os
import numpy as np
from math import ceil
import pywt
import bitarray
import matlab.engine
from PIL import Image
import time, socket
sys.path.append('.')
from dwt_lib import load_img
from fountain_lib import Fountain, Glass
from fountain_lib import EW_Fountain, EW_Droplet
from spiht_dwt_lib import spiht_encode, func_DWT, code_to_file, spiht_decode, func_IDWT

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
SIM_PATH = os.path.join(LIB_PATH, '../simulation')
WHALE_IMG= os.path.join(DOC_PATH, 'whale.bmp')
LENA_IMG = os.path.join(DOC_PATH, 'lena.png')

HOST = '127.0.0.1'
PORT = 9999



class Sender():
    def __init__(self, img_path, 
            level=3, 
            wavelet='bior4.4', 
            mode = 'periodization',
            fountain_chunk_size = 1000,
            fountain_type= 'normal',
            drop_interval=5,
            port=PORT,
            w1_size=0.1,
            w1_pro=0.084,
            seed=None):
        self.drop_id = 0
        self.eng = matlab.engine.start_matlab()
        self.eng.addpath(LIB_PATH)
        self.img_path = img_path
        self.fountain_chunk_size = fountain_chunk_size
        self.fountain_type = fountain_type
        self.drop_interval=drop_interval
        self.w1_p=w1_size
        self.w1_pro=w1_pro
        self.port=port
        self.seed=seed

        #  三通道一起处理
        temp_file = self.img_path#  .replace(self.img_path.split('/')[-1], 'tmp')
        rgb_list = ['r', 'g', 'b']
        temp_file_list = [temp_file + '_' + ii for ii in rgb_list]
        if self.is_need_img_process():
            print('process imgage: {:s}'.format(self.img_path))
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
            self.dwt_coeff = [func_DWT(ii) for ii in self.img_mat]
            self.spiht_bits = [spiht_encode(ii, self.eng) for ii in self.dwt_coeff]

            #  trick 
            a =[code_to_file(self.spiht_bits[ii],
                temp_file_list[ii],
                add_to=self.fountain_chunk_size / 3 * 8) 
                    for ii in range(len(rgb_list))]
        else :           
            print('temp file found : {:s}'.format(self.img_path))
        self.m, _chunk_size = self._321(temp_file_list, each_chunk_size=int(self.fountain_chunk_size / 3))

        #  暂时只有 r, 没有 g b
        #  code_to_file(self.spiht_bits[0], temp_file)
        #  m = open(temp_file, 'r').read()
        self.write_fd = self.socket_builder()

        self.fountain = self.fountain_builder()

        #  a = [os.remove(ii) for ii in temp_file_list]
        self.show_info()
        #  self.send_drops_use_socket()
    def socket_builder(self):
        socket_send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_send.bind((HOST, self.port))
        socket_send.listen(1)
        print('waitting for connect........')
        write_fd, addr = socket_send.accept()
        print('connected')
        return write_fd


    def fountain_builder(self):
        if self.fountain_type == 'normal':
            return Fountain(self.m, chunk_size=self.fountain_chunk_size, seed=self.seed)
        elif self.fountain_type == 'ew':    
            return EW_Fountain(self.m, 
                    chunk_size=self.fountain_chunk_size,
                    w1_size=self.w1_p,
                    w1_pro=self.w1_pro,
                    seed=self.seed)


    def show_info(self):
        self.fountain.show_info()


    def a_drop(self):
        return self.fountain.droplet().toBytes()
    

    def send_drops_use_socket(self):
        packet_discard_rate = 0.1
        discard_one = int(1 / packet_discard_rate)
        while True:
            time.sleep(self.drop_interval)
            self.drop_id += 1
            if self.drop_id % discard_one == 0:
                print("discard one")
                self.a_drop()
            else:
                print('drop id : ', self.drop_id)
                self.write_fd.send(self.a_drop())

    def _321(self, file_list, each_chunk_size=2500):
        '''
        将三个文件和并为一个文件
        '''
        #  m_list = [open(ii, 'r').read() for ii in file_list]
        m_list = []
        m_list.append(open(file_list[0], 'r').read())
        m_list.append(open(file_list[1], 'r').read())
        m_list.append(open(file_list[2], 'r').read())

        #  a = [print(len(ii)) for ii in m_list]
        m = ''
        for i in range(int(ceil(len(m_list[0]) / float(each_chunk_size)))):
            start = i * each_chunk_size
            end = min((i + 1) * each_chunk_size, len(m_list[0]))
            #  m += ''.join([ii[start:end] for ii in m_list])
            m += m_list[0][start: end]
            m += m_list[1][start: end]
            m += m_list[2][start: end]
            #  print(len(m))            
        return m, each_chunk_size * 3

    def is_need_img_process(self):
        #  print(sys._getframe().f_code.co_name)

        doc_list = os.listdir(os.path.dirname(self.img_path))
        img_name = self.img_path.split('/')[-1]
        suffix = ['_' + ii  for ii in list('rbg')]
        target = [img_name + ii for ii in suffix]
        count = 0
        for t in target:
            if t in doc_list:
                count += 1
        if count == 3:
            return False
        else:
            return True



class EW_Sender(Sender):
    def __init__(self, img_path, fountain_chunk_size, seed=None):
        Sender.__init__(self, img_path, fountain_chunk_size=fountain_chunk_size, fountain_type='ew', seed=seed)


class Receiver():
    def __init__(self):
        self.drop_id = 0
        self.eng = matlab.engine.start_matlab()
        self.eng.addpath(LIB_PATH)
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
        self.test_dir = os.path.join(SIM_PATH,time.asctime().replace(' ', '_').replace(':', '_'))
        os.mkdir(self.test_dir)
        self.socket_recv = self.socket_builder()

        while True:
            self.begin_to_catch()
            if self.glass.isDone():
                self.socket_recv.close()
                print('recv done')
                break
        
    def socket_builder(self):
        socket_recv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_recv.connect((HOST, PORT))
        return socket_recv
 

    def add_a_drop(self, d_byte):
        a_drop = self.glass.droplet_from_Bytes(d_byte)

        if self.glass.num_chunks == 0:
            print('init num_chunks : ', a_drop.num_chunks)
            self.glass = Glass(a_drop.num_chunks)
            self.chunk_size = len(a_drop.data)

        self.glass.addDroplet(a_drop)
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
            except :
                print('decode error in matlab')

    def catch_a_drop_use_socket(self):
        return self.socket_recv.recv(self.drop_byte_size)


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

    def begin_to_catch(self):
        a_drop = self.catch_a_drop_use_socket()
        if not a_drop == None:
            self.drop_id += 1
            print("drops id : ", self.drop_id)
            self.drop_byte_size = len(a_drop)
            self.add_a_drop(a_drop)
    
    def _123(self, bits, chunk_size):
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
            end = min((i+1)*chunk_size, int(bits.length())) * 8
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
            except :
                print('decode error in matlab')


if __name__ == "__main__":
    sender = Sender(LENA_IMG)
    #  receiver = Receiver()
    pass
