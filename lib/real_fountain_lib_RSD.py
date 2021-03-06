# _*_ coding=utf-8 _*_
from __future__ import print_function
from math import ceil, log
import sys, os
import random
import json
import bitarray
import numpy as np
from time import sleep
import time
import logging
import pandas as pd

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
SIM_PATH = os.path.join(LIB_PATH, '../simulation')

logging.basicConfig(level=logging.INFO, 
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s-%(message)s",)

def charN(str, N):
    if N < len(str):
        return str[N]
    return 'X'

def xor(str1, str2):
    '''
    按位运算str1, str2
    将 str1 和 str2 中每一个字符转为acsii 表中的编号，再将两个编号转为2进制按位异或运算
    ，最后返回异或运算的数字在ascii 表中的字符
    '''
    length = max(len(str1),len(str2))
    a1 = charN(str1, 700)
    a2 = charN(str2, 700)
    return ''.join(chr(ord(charN(str1,i)) ^ ord(charN(str2,i))) for i in range(length))

def x_o_r(bytes1, bytes2):  # 传入两个数，并返回它们的异或结果，结果为16进制数
    length = max(len(bytes1), len(bytes2))

    if len(bytes1) < len(bytes2):
        add_num = len(bytes2) - len(bytes1)
        bytes1_array = bytearray(bytes1)
        add = b'0'*add_num

        for ii in range(add_num):
            bytes1_array.insert(0, add[ii])
            bytes1 = bytes(bytes1_array)

    else:
        add_num = len(bytes1) - len(bytes2)
        bytes2_array = bytearray(bytes2)
        add = b'0' * add_num

        for ii in range(add_num):
            bytes2_array.insert(0, add[ii])
            bytes2 = bytes(bytes2_array)

    result_bytes = b''
    for i in range(length):
        result_bytes += (bytes1[i] ^ bytes2[i]).to_bytes(1, 'little')

    return result_bytes

# 度分布函数
def soliton(K):
    ''' 理想弧波函数 '''
    d = [ii + 1 for ii in range(K)]
    d_f = [1.0 / K if ii == 1 else 1.0 / (ii * (ii - 1)) for ii in d]
    while 1:
        # i = np.random.choice(d, 1, False, d_f)[0]
        yield np.random.choice(d, 1, False, d_f)[0]

# dafualt: 0.03 0.05 
def robust_soliton(K, c= 0.03, delta= 0.05):
    # c是自由变量，delta是接收到M个确知数据包后无法译码的概率极限。c确定时delta越大R越小
    ''' 鲁棒理想弧波函数 '''
    d = [ii + 1 for ii in range(K)]
    soliton_d_f = [1.0 / K if ii == 1 else 1.0 / (ii * (ii - 1)) for ii in d]

    R = c * log(K / delta) * (K ** 0.5)                         # 每次解码中度数为1的编码符号的数目
    d_interval_0 = [ii + 1 for ii in list(range(int(round(K / R)) - 1))]
    d_interval_1 = [int(round(K / R))]
    tau = [R / (K * dd) if dd in d_interval_0
            else R / float(K) * log(R / delta) if dd in d_interval_1
            else 0 for dd in d]

    Z = sum([soliton_d_f[ii] + tau[ii] for ii in range(K)])
    u_d_f = [(soliton_d_f[ii] + tau[ii]) / Z for ii in range(K)]    #概率密度分布函数

    while True :
        # i = np.random.choice(d, 1, False, u_d_f)[0]
        yield np.random.choice(d, 1, False, u_d_f)[0]             # 返回一个度值

def fixed_degree_distribution_func():
#'''Shokrollahi, 5.78'''
    d = [1, 2, 3, 4, 5, 8, 9, 19, 65, 66]
    d_f = [0.007969, 0.49357, 0.16622, 0.072646, 0.082558, 0.056058, 0.037229, 0.05559, 0.025023, 0.003137]
    while True:
        i = np.random.choice(d, 1, False, d_f)[0]
        yield i

def poisson_func(k):
    d = [1, 2, 3, 4, 5, 8, 9, 19, 65, 66]
    tmp = 1.0 / (k * log(k))
    d_f = [0.003269+65*tmp, 0.49357-17*tmp, 0.16622-33*tmp, 0.072646-15*tmp, 0.082558-tmp, 0.056028-9*tmp, 0.037229+8*tmp, 0.05559, 0.029723-tmp, 0.003167+3*tmp]
    while True:
        yield np.random.choice(d, 1, False, d_f)[0]

def binary_exp_func(k):
    d = [ii + 1 for ii in range(k)] 
    d_f = [1.0 / 2**(k-1) if ii == k else 1.0 / (2 ** ii) for ii in d]
    while True:
        yield np.random.choice(d, 1, False, d_f)[0]

def switch_distribution_func(i, a, k):
    while True:
        if i <= a * k:
            yield binary_exp_func(k)
        else:
            yield robust_soliton(k)


# 通过度值随机选择数据块编号
def randChunkNums(num_chunks):
    '''
    size 是每次选取的度数，这里选取的是一个度函数，size 分布是
    度函数的文章要在这里做, 这里的度函数是一个 5 到 K 的均匀分布
    num_chunks : int, 编码块总数量
    return : list, 被选中的编码块序号
    '''
    size = random.randint(1,min(5, num_chunks))
    # random.sample 是一个均匀分布的采样
    return random.sample(range(num_chunks), size)

def robust_randChunkNums(num_chunks):
    size = robust_soliton(num_chunks).__next__()
    return [ii for ii in random.sample(range(num_chunks), size)]

def all_at_once_randChunkNums(chunks):
    # return random.sample(chunks, 1)
    return [ii for ii in np.random.choice(chunks, 1, False)]

def switch_randChunkNums(chunk_id, num_chunks, a=0.075):
    if chunk_id <= a * num_chunks:
        size = binary_exp_func(num_chunks).__next__()
    else:
        size = robust_soliton(num_chunks).__next__()
    return [ii for ii in random.sample(range(num_chunks), size)]

def fixed_degree_randChunkNums(num_chunks):
    size = fixed_degree_distribution_func().__next__()
    return [ii for ii in random.sample(range(num_chunks), size)]

def mfixed_degree_randChunkNums(num_chunks):
    size = poisson_func(num_chunks).__next__()
    return [ii for ii in random.sample(range(num_chunks), size)]



class Droplet:
    ''' 储存随机数种子，并有一个计算本水滴中包含的数据块编码的方法'''
    def __init__(self, data, seed, num_chunks, process, func_id, feedback_idx):
        self.data = data
        self.seed = seed
        self.num_chunks = num_chunks
        self.process = process

        self.func_id = func_id
        self.feedback_idx = feedback_idx

    def robust_chunkNums(self):
        random.seed(self.seed)
        np.random.seed(self.seed)
        return robust_randChunkNums(self.num_chunks)
    
    def all_at_once_chunkNums(self):
        random.seed(self.seed)
        np.random.seed(self.seed)
        return all_at_once_randChunkNums(self.process)

    def fixed_degree_chunkNums(self):
        random.seed(self.seed)
        np.random.seed(self.seed)
        return fixed_degree_randChunkNums(self.num_chunks)

    def mfixed_degree_ChunkNums(self):
        random.seed(self.seed)
        np.random.seed(self.seed)
        return mfixed_degree_randChunkNums(self.num_chunks)


    def toBytes(self):
        '''
        使用一个字节存储chunks_size,
        num_chunks int 度数，一个字节                                  2个字节？
        seed 随机数种子，两个字节                                       4个字节？
        返回的结构是一个字节加后面跟着2 * n 个字节，后续跟着数据
        '''
        num_chunks_bits = format(int(self.num_chunks), "016b")
        seed_bits = format(int(self.seed), "032b")
        logging.info('fountain num_chunks : {}, seed : {}'.format(self.num_chunks, self.seed))

        return bitarray.bitarray(num_chunks_bits + seed_bits).tobytes() + self.data



class Fountain(object):
    # 继承了object对象，拥有了好多可操作对象，这些都是类中的高级特性。python 3 中已经默认加载了object
    def __init__(self, data, chunk_size, seed=None):
        self.data = data
        self.chunk_size = chunk_size
        self.num_chunks = int(ceil(len(data) / float(chunk_size)))
        self.seed = seed
        self.all_at_once = False
        self.chunk_selected = []
        self.chunk_process = []
        random.seed(seed)
        np.random.seed(seed)

        self.func_id = 0
        self.feedback_idx = 0
        self.dropid = 0

    def show_info(self):
        logging.info('Fountain info')
        logging.info('data len: {}'.format(len(self.data)))
        logging.info('chunk_size: {}'.format(self.chunk_size))
        logging.info('num_chunks: {}'.format(self.num_chunks))

    def droplet(self):
        self.dropid += 1
        self.updateSeed()
        ### 修改
        if not self.all_at_once:
            self.chunk_selected = robust_randChunkNums(self.num_chunks)
        else:
            self.func_id = 1
            self.chunk_selected = all_at_once_randChunkNums(self.chunk_process)

        data = None
        for num in self.chunk_selected:
            if data is None:
                data = self.chunk(num)
            else:
                data = xor(data, self.chunk(num))
                # data = x_o_r(data, self.chunk(num))               # 被选到的数据块异或   异或时存在两字符串长度不一样

        return Droplet(data, self.seed, self.num_chunks, self.chunk_process, self.func_id, self.feedback_idx)

    def chunk(self, num):
        start = self.chunk_size * num
        end = min(self.chunk_size * (num+1), len(self.data))
        return self.data[start:end]

    def updateSeed(self):
        self.seed = random.randint(0, 2**31-1)
        random.seed(self.seed)
        np.random.seed(self.seed)



class EW_Fountain(Fountain):
    ''' 扩展窗喷泉码 '''
    def __init__(self, data, chunk_size, seed=None, ew_process=[], w1_size=0.6, w1_pro=0.6):
        Fountain.__init__(self, data, chunk_size=chunk_size, seed=None)
        # logging.info("-----------------EW_Fountain------------")
        self.w1_p = w1_size
        self.w1_pro = w1_pro
        self.windows_id_gen = self.windows_selection()
        self.w1_size = int(round(self.num_chunks * self.w1_p))
        self.w2_size = self.num_chunks
        self.w1_random_chunk_gen = robust_soliton(self.w1_size),
        self.w2_random_chunk_gen = robust_soliton(self.w2_size)

        self.all_at_once = False
        self.chunk_process = ew_process
        self.chunk_selected = []
        self.func_id = 0
        self.feedback_idx = 0

        self.dropid = 0

    def droplet(self):
        self.dropid += 1
        self.updateSeed()
        if not self.all_at_once:
            self.chunk_selected = self.EW_robust_RandChunkNums(self.num_chunks)
        else:
            self.func_id = 1
            self.chunk_selected = self.EW_all_at_once_RandChunkNums()
        data = None
        for num in self.chunk_selected:
            if data is None:
                data = self.chunk(num)
            else:
                data = xor(data, self.chunk(num))
                # data = x_o_r(data, self.chunk(num))

        return EW_Droplet(data, self.seed, self.num_chunks, self.chunk_process, self.func_id, self.feedback_idx, self.w1_p, self.w1_pro)

    def EW_robust_RandChunkNums(self, num_chunks):
        '''扩展窗的不同在这里'''
        window_id = self.windows_id_gen.__next__()
        if window_id == 1:
            size = self.w1_random_chunk_gen[0].__next__()          # 鲁棒孤波返回的度值
            return random.sample(range(self.w1_size), size)
        else:
            size = self.w2_random_chunk_gen.__next__()
            return [ii for ii in random.sample(range(self.w2_size), size)]

    def EW_all_at_once_RandChunkNums(self):
        # w1未译出的块
        w1_chunk_process = []
        for i in self.chunk_process:
            if i <= self.w1_size:
                w1_chunk_process.append(i)

        window_id = self.windows_id_gen.__next__()
        if window_id == 1 and len(w1_chunk_process)>0:
            return [ii for ii in np.random.choice(w1_chunk_process, 1, False)]  
        else:
            return [ii for ii in np.random.choice(self.chunk_process, 1, False)]

    def windows_selection(self):
        '''以概率[{p:1, 1-p:2}返回选择的窗口'''
        d = [1, 2]
        w1_p = self.w1_pro
        w_f = [w1_p, 1-w1_p]
        while True:
            i = np.random.choice(d, 1, False, w_f)[0]    # 从d中以概率w_f，随机选择1个,replace抽样之后还放不放回去
            yield i



class EW_Droplet(Droplet):
    '''扩展窗喷泉码专用水滴, 计算水滴使用的数据块列表'''
    def __init__(self, data, seed, num_chunks, process, func_id, feedback_idx, w1_size=0.6, w1_pro=0.6):
        Droplet.__init__(self, data=data, seed=seed, num_chunks=num_chunks, process=process, func_id=func_id, feedback_idx=feedback_idx)
        m = ' ' * num_chunks * len(data)
        self.ower = EW_Fountain(m, len(self.data),  ew_process=process, w1_size=w1_size, w1_pro=w1_pro)

    def robust_chunkNums(self):
        random.seed(self.seed)
        np.random.seed(self.seed)
        return self.ower.EW_robust_RandChunkNums(self.num_chunks)

    def all_at_once_chunkNums(self):
        random.seed(self.seed)
        np.random.seed(self.seed)
        return self.ower.EW_all_at_once_RandChunkNums()


class Glass:
    '''接收水滴：与或计算后的数据，'''
    def __init__(self, num_chunks):
        self.entries = []
        self.droplets = []
        self.num_chunks = num_chunks
        self.chunks = [None] * num_chunks
        self.chunk_bit_size = 0
        self.dropid = 0
        self.all_at_once = False

        self.feedback_dropid = 0
        self.process = []
        self.process_history = []

        self.w1_done_dropid = 0
        self.w1_done = False
        
    def addDroplet(self, drop):
        self.dropid += 1
        self.droplets.append(drop)
        # logging.info("recv seed: {}\tnum_chunks: {}".format(drop.seed, drop.num_chunks))    # \t=tab
        # drop.chunkNums()方法通过seed生成的所选数据块与fountain一样
        entry = [drop.robust_chunkNums(), drop.data] if drop.func_id==0 else [drop.all_at_once_chunkNums(), drop.data]
        self.entries.append(entry)
        # logging.info('recv chunk_list : {}'.format(entry[0]))
        self.updateEntry(entry)

    def droplet_from_Bytes(self, d_bytes):
        byte_factory = bitarray.bitarray(endian='big')
        byte_factory.frombytes(d_bytes[0:2])
        num_chunks = int(byte_factory.to01(), base=2)

        byte_factory1 = bitarray.bitarray(endian='big')
        byte_factory1.frombytes(d_bytes[2:6])
        seed = int(byte_factory1.to01(), base=2)

        data = d_bytes[6:]

        logging.info(' seed: {}\tglass num_chunks : {}\t data len: {},'.format(seed, num_chunks, len(data)))
        if self.chunk_bit_size == 0:
            byte_factory2 = bitarray.bitarray(endian='big')
            byte_factory2.frombytes(data)
            self.chunk_bit_size = byte_factory2.length()

        d = Droplet(data, seed, num_chunks)
        return d

    def updateEntry(self, entry):
        '''
        BP 译码算法
        #  logging.info(entry[0])
        #  entry 是一个解码缓存结果
        #  entry[0] 是喷泉码编码时选中的源符号编号列表，长度即为度
        #  entry[1] 是喷泉码选中的符号 xor 后的结果
        #  chunk 是解码后的结果
        '''
        #  下面的 for 用于更新 entry 中的水滴，若水滴中包含已解码的码块，则将该部分去除
        #  执行结果是 entry 中的水滴不包含已解码的码块，度会减少或不变
        for chunk_num in entry[0]:
            if self.chunks[chunk_num] is not None:
                entry[1] = xor(entry[1], self.chunks[chunk_num])
                # entry[1] = x_o_r(entry[1], self.chunks[chunk_num])
                entry[0].remove(chunk_num)
        #  若度为 1,则说明该度的码块已经被解码出来，更新 chunk 后继续进行entry 中的其他
        #  元素的更新
        if len(entry[0]) == 1:
            self.chunks[entry[0][0]] = entry[1]
            self.entries.remove(entry)
            for former_entry in self.entries:
                if entry[0][0] in former_entry[0]:
                    self.updateEntry(former_entry)
                    
    def getString(self):
        return ''.join(x or ' _ ' for x in self.chunks)

    def get_bits(self):
        current_bits = ''
        bitarray_factory = bitarray.bitarray(endian='big')
        logging.info('current chunks')
        logging.info([ii if ii == None else '++++' for ii in self.chunks])

        for chunk in self.chunks:
            if chunk == None:
                break
            else:
                tmp = bitarray_factory.frombytes(chunk)
        return bitarray_factory

    def get_w1_bits(self, w1_size):
        current_bits = ''
        bitarray_factory = bitarray.bitarray(endian='big')
        logging.info('current chunks')
        logging.info([ii if ii == None else '++++' for ii in self.chunks])

        for chunk in self.chunks[:int(round(self.num_chunks * w1_size))]:
            if chunk == None:
                break
            else:
                # for ii in chunk:
                # a = str(ii)
                tmp = bitarray_factory.frombytes(chunk)
        return bitarray_factory

    def isDone(self):
        return (None not in self.chunks) and (len(self.chunks) != 0) 

    # 返回未译出码块
    def getProcess(self):
        idx = 0
        process = []
        for chunk in self.chunks:
            if chunk is None:
                process.append(idx)
            idx += 1
        return process

    def is_w1_done(self, w1_size):
        if None not in self.chunks[:int(round(self.num_chunks * w1_size))]:
            if self.w1_done == False:
                self.w1_done_dropid = self.dropid
                self.w1_done = True
            return True
        else:
            return False 

    def chunksDone(self):
        count = 0
        for c in self.chunks:
            if c is not None:
                count+=1
        return count


# 不同码长K与译码开销的关系
suffix_list = ['123.txt']
suffix_list = ['152.txt']

# suffix_list = ['115.txt']

suffix_list = ['50.txt', '100.txt', '150.txt', '200.txt', '250.txt', '300.txt', '350.txt', '400.txt', '450.txt', '500.txt', '550.txt', '600.txt', '650.txt', '700.txt','750.txt','800.txt','850.txt','900.txt','950.txt','1000.txt']
# suffix_list = ['900.txt','950.txt','1000.txt']
# suffix_list = ['50.txt']
def test_LT_fountain_K():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_drops_list = [0]*len(suffix_list)
    avg_idx = 0

    for f in file_list:
        m = open(f, 'r').read()
        # 测试1000次
        num_chunks_list = [0]*100
        times_list = [0]*100
        drop_num_used_list = [0]*100

        times = 0
        K = 0
        while times < 100:
            fountain = Fountain(m, 1)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            while not glass.isDone():
                a_drop = fountain.droplet()       # send

                glass.addDroplet(a_drop)          # recv
                # logging.info('+++++++++++++++++++++++++++++')
                # logging.info(glass.getString())

            num_chunks_list[times] = fountain.num_chunks
            times_list[times] = times
            drop_num_used_list[times] = glass.dropid

            logging.info("K=" + str(fountain.num_chunks) +" times: " + str(times) + 'done, receive_drop_used: ' + str(glass.dropid))
            times += 1

        # res = pd.DataFrame({'num_chunks':num_chunks_list, 
        #     'times':times_list, 
        #     'drop_num_used':drop_num_used_list})
        # res.to_csv(os.path.join(SIM_PATH, 'K' + '_'+ str(K) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_drops_list[avg_idx] = float(sum(drop_num_used_list) / len(drop_num_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'K': [ii.split('.')[0] for ii in suffix_list], 
            'avgs':avg_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

def test_LT_feedback_fountain_K():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_drops_list = [0]*len(suffix_list)
    avg_idx = 0

    avg_acknums_list = [0]*len(suffix_list)
    ack_idx = 0

    for f in file_list:
        m = open(f, 'r').read()
        # 测试1000次
        num_chunks_list = [0]*100
        times_list = [0]*100
        drop_num_used_list = [0]*100
        acknums_list = [0]*100

        times = 0
        K = 0
        while times < 100:
            fountain = Fountain(m, 1)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            ack_num = 0
            while not glass.isDone():
                a_drop = fountain.droplet()       # send
                    
                glass.addDroplet(a_drop)          # recv
                if(glass.dropid >= K):
                    glass.all_at_once = True
                    fountain.all_at_once = True
                    # 之后每10个包反馈进度
                    if((glass.dropid-K)%25 == 0):
                        ack_num += 1
                        fountain.chunk_process = glass.getProcess()
                

                # logging.info('+++++++++++++++++++++++++++++')
                # logging.info(glass.getString())

            num_chunks_list[times] = fountain.num_chunks
            times_list[times] = times
            drop_num_used_list[times] = glass.dropid
            acknums_list[times] = ack_num

            logging.info("feedback_K=" + str(fountain.num_chunks) +" times: " + str(times) + 'done, receive_drop_used: ' + str(glass.dropid))
            times += 1

        res = pd.DataFrame({'num_chunks':num_chunks_list, 
            'times':times_list, 
            'drop_num_used':drop_num_used_list})
        res.to_csv(os.path.join(SIM_PATH, 'RSD_LT/K_25/feedback_K' + '_'+ str(K) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_drops_list[avg_idx] = float(sum(drop_num_used_list) / len(drop_num_used_list))
        avg_idx += 1
        avg_acknums_list[ack_idx] = float(sum(acknums_list) / len(acknums_list))
        ack_idx += 1
    
    avg_res = pd.DataFrame({'K': [ii.split('.')[0] for ii in suffix_list], 
            'avgs':avg_drops_list, 'feedback_packet_avgs':avg_acknums_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'RSD_LT/K_25/feedback_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

def test_ew_fountain_K():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    w1_avg_drops_list = [0]*len(suffix_list)
    w2_avg_drops_list = [0]*len(suffix_list)
    avg_idx = 0

    for f in file_list:
        m = open(f, 'r').read()
        # 测试1000次
        num_chunks_list = [0]*100
        times_list = [0]*100
        w1_drop_num = [0]*100
        w2_drop_num = [0]*100

        times = 0
        K = 0
        while times < 100:
            fountain = EW_Fountain(m, 1)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            ew_drop = None
            w1_done_dropid = 0
            while not glass.isDone():
                a_drop = fountain.droplet()       # send
                if a_drop.func_id==0:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=[], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)
                else:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=glass.process_history[a_drop.feedback_idx], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)


                glass.addDroplet(ew_drop)          # recv
                if glass.is_w1_done(0.6):
                    w1_done_dropid = glass.w1_done_dropid

            num_chunks_list[times] = fountain.num_chunks
            times_list[times] = times
            w1_drop_num[times] = w1_done_dropid
            w2_drop_num[times] = glass.dropid

            logging.info("EW K=" + str(fountain.num_chunks) +" times: " + str(times) + 'done, w1_drops: ' + str(w1_done_dropid) + ', w2_drops: ' + str(glass.dropid))
            times += 1

        res = pd.DataFrame({'num_chunks':num_chunks_list, 
            'times':times_list, 
            'w1_drop_num':w1_drop_num,
            'w2_drop_num':w2_drop_num})
        res.to_csv(os.path.join(SIM_PATH, 'EW(0.6, 0.6)/RSD/no_feedback/100次/EW_K' + '_'+ str(K) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        w1_avg_drops_list[avg_idx] = float(sum(w1_drop_num) / len(w1_drop_num))
        w2_avg_drops_list[avg_idx] = float(sum(w2_drop_num) / len(w2_drop_num))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'K': [ii.split('.')[0] for ii in suffix_list], 
            'w1_avg_drops':w1_avg_drops_list,
            'w2_avg_drops':w2_avg_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'EW(0.6, 0.6)/RSD/no_feedback/100次/EW_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

def test_ew_feedback_fountain_K():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    w1_avg_drops_list = [0]*len(suffix_list)
    w2_avg_drops_list = [0]*len(suffix_list)
    avg_idx = 0
    avg_acknums_list = [0]*len(suffix_list)
    ack_idx = 0

    for f in file_list:
        m = open(f, 'r').read()
        # 测试次数
        max_test_times = 200
        num_chunks_list = [0]*max_test_times
        times_list = [0]*max_test_times
        w1_drop_num = [0]*max_test_times
        w2_drop_num = [0]*max_test_times
        acknums_list = [0]*max_test_times

        times = 0
        K = 0
        while times < max_test_times:
            fountain = EW_Fountain(m, 1)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            ack_num = 0
            ew_drop = None
            w1_done_dropid = 0
            send_drops = 0
            feedback_send_drops = 0
            sender_get_process = False
            Y_N = ''
            while not glass.isDone():
                a_drop = fountain.droplet()       # send
                if a_drop.func_id==0:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=[], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)
                else:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=glass.process_history[a_drop.feedback_idx], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)
                send_drops += 1

                pack_loss = [True, False]
                prob_loss = [0.04, 0.96]
                pack_loss_flag = np.random.choice(pack_loss, 1, False, prob_loss)[0]
                if pack_loss_flag==False:             # 丢包
                    glass.addDroplet(ew_drop)         # recv
                
                    # n1 = round(0.5*K)
                    # n2 = 30
                    # if(glass.dropid >= n1):
                    #     # 获得反馈时进度
                    #     if (glass.dropid - n1) % n2== 0:
                    #         glass.process = glass.getProcess()
                    #         glass.process_history.append(glass.process)
                    #         glass.feedback_dropid = glass.dropid
                    #     # 发送端延迟获得反馈，这里可能随机收到[18*(1-per), 18]个
                    #     if(glass.dropid - glass.feedback_dropid == 18):
                    #         fountain.all_at_once = True
                    #         fountain.chunk_process = glass.process
                    #         fountain.feedback_idx = ack_num
                    #         ack_num += 1
                    #     if(glass.is_w1_done(0.6)):
                    #         w1_done_dropid = glass.w1_done_dropid
                    
                    # 对比方案：w1done之后每30个包反馈
                    n2 = 30
                    if(glass.is_w1_done(0.6)):
                        w1_done_dropid = glass.w1_done_dropid
                        # 获得反馈时进度
                        if (glass.dropid - glass.w1_done_dropid) % n2== 0:
                            glass.process = glass.getProcess()
                            glass.process_history.append(glass.process)
                            feedback_send_drops = send_drops
                            sender_get_process = True
                # 发送端延迟获得反馈
                if sender_get_process == True and (send_drops - feedback_send_drops == 18):
                    fountain.all_at_once = True
                    fountain.chunk_process = glass.process
                    fountain.feedback_idx = ack_num
                    ack_num += 1
                    sender_get_process = False

            if m==glass.getString():
                Y_N = 'Y'
            else:
                Y_N = 'N'

            num_chunks_list[times] = fountain.num_chunks
            times_list[times] = times
            w1_drop_num[times] = w1_done_dropid
            w2_drop_num[times] = glass.dropid
            acknums_list[times] = ack_num

            logging.info("feedback_EW_K=" + str(fountain.num_chunks) +" times: " + str(times) + 'done, w1_drops: ' + str(w1_done_dropid) + ', w2_drops: ' + str(glass.dropid) + ' ' + Y_N)
            times += 1

        res = pd.DataFrame({'num_chunks':num_chunks_list, 
            'times':times_list, 
            'w1_drop_num':w1_drop_num,
            'w2_drop_num':w2_drop_num,
            'feedback_num':acknums_list})
        res.to_csv(os.path.join(SIM_PATH, 'EW(0.6, 0.6)/RSD/水声反馈/w1done_30/18个可能有丢包/feedback_RSD_EW_K' + '_'+ str(K) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        w1_avg_drops_list[avg_idx] = float(sum(w1_drop_num) / len(w1_drop_num))
        w2_avg_drops_list[avg_idx] = float(sum(w2_drop_num) / len(w2_drop_num))
        avg_idx += 1
        avg_acknums_list[ack_idx] = float(sum(acknums_list) / len(acknums_list))
        ack_idx += 1
    
    avg_res = pd.DataFrame({'K': [ii.split('.')[0] for ii in suffix_list], 
            'w1_avg_drops':w1_avg_drops_list, 
            'w2_avg_drops':w2_avg_drops_list, 
            'feedback_packet_avgs':avg_acknums_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'EW(0.6, 0.6)/RSD/水声反馈/w1done_30/18个可能有丢包/feedback_RSD_EW_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

# 不同w1_pro与译码开销的关系
def test_ew_w1pro_overhead():
    w1_pro_list = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    w1_pro_list = [0.9]
    w1_avg_drops_list = [0]*len(w1_pro_list)
    w2_avg_drops_list = [0]*len(w1_pro_list)
    avg_idx = 0

    for p in w1_pro_list:
        m = open(DOC_PATH + '/text115.txt', 'r').read()
        # 测试100次
        w1pro_list = [0]*100
        times_list = [0]*100
        w1_drops_used_list = [0]*100
        w2_drops_used_list = [0]*100

        times = 0
        K = 0
        while times < 100:
            fountain = EW_Fountain(m, 1, w1_size=0.6, w1_pro=p)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            ew_drop = None
            w1_done = False
            while not glass.isDone():
                a_drop = fountain.droplet()       # send
                ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, a_drop.process, w1_size=0.6, w1_pro=p)

                glass.addDroplet(ew_drop)          # recv

                if w1_done == False:
                    if glass.is_w1_done(0.6):
                        w1_drops_used_list[times] = glass.w1_done_dropid
                        w1_done = True

            w1pro_list[times] = p
            times_list[times] = times
            w2_drops_used_list[times] = glass.dropid

            logging.info("EW(w1_size=0.6) w1_pro=" + str(p) +" times: " + str(times) + 'done, w1_drops_used: ' + str(glass.w1_done_dropid) + ', w2_drops_used: '+ str(glass.dropid))
            times += 1

        res = pd.DataFrame({'w1_pro':w1pro_list, 
            'times':times_list, 
            'w1_drops_used':w1_drops_used_list,
            'w2_drops_used':w2_drops_used_list})
        res.to_csv(os.path.join(SIM_PATH, 'w1_pro选择/EW_RSD(w1_size=0.6)_w1_pro=' + str(p) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        w1_avg_drops_list[avg_idx] = float(sum(w1_drops_used_list) / len(w1_drops_used_list))
        w2_avg_drops_list[avg_idx] = float(sum(w2_drops_used_list) / len(w2_drops_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'w1_pro': w1_pro_list, 
            'w1_avgs': w1_avg_drops_list,
            'w2_avgs': w2_avg_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'w1_pro选择/EW_RSD(w1_size=0.6)_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

# 不同w1_pro与译码开销的关系(水声反馈)
def test_feedback_ew_w1pro_overhead():
    w1_pro_list = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    w1_avg_drops_list = [0]*len(w1_pro_list)
    w2_avg_drops_list = [0]*len(w1_pro_list)
    avg_idx = 0

    for p in w1_pro_list:
        m = open(DOC_PATH + '/text115.txt', 'r').read()
        # 测试100次
        w1pro_list = [0]*100
        times_list = [0]*100
        w1_drops_used_list = [0]*100
        w2_drops_used_list = [0]*100

        times = 0
        K = 0
        while times < 100:
            fountain = EW_Fountain(m, 1, w1_size=0.6, w1_pro=p)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            ew_drop = None
            w1_done = False
            ack_num = 0
            while not glass.isDone():
                a_drop = fountain.droplet()       # send
                if a_drop.func_id==0:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=[], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx, w1_size=0.6, w1_pro=p)
                else:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=glass.process_history[a_drop.feedback_idx], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx, w1_size=0.6, w1_pro=p)

                glass.addDroplet(ew_drop)          # recv

                if w1_done == False:
                    if glass.is_w1_done(0.6):
                        w1_drops_used_list[times] = glass.w1_done_dropid
                        w1_done = True

                n1 = round(0.6*K)
                n2 = 30
                if(glass.dropid >= n1):
                    # 获得反馈时进度
                    if (glass.dropid - n1) % n2== 0:
                        glass.process = glass.getProcess()
                        glass.process_history.append(glass.process)
                        glass.feedback_dropid = glass.dropid
                    # 发送端延迟获得反馈，这里可能随机收到[18*(1-per), 18]个
                    if(glass.dropid - glass.feedback_dropid == 18):
                        fountain.all_at_once = True
                        fountain.chunk_process = glass.process
                        fountain.feedback_idx = ack_num
                        ack_num += 1
                
                # 对比方案：w1done之后每30个包反馈
                # n2 = 30
                # if(glass.is_w1_done(0.6)):
                #     # 获得反馈时进度
                #     if (glass.dropid - glass.w1_done_dropid) % n2== 0:
                #         glass.process = glass.getProcess()
                #         glass.process_history.append(glass.process)
                #         glass.feedback_dropid = glass.dropid
                #     # 发送端延迟获得反馈，这里可能随机收到[18*(1-per), 18]个
                #     if(glass.dropid - glass.feedback_dropid == 18):
                #         fountain.all_at_once = True
                #         fountain.chunk_process = glass.process
                #         fountain.feedback_idx = ack_num
                #         ack_num += 1

            w1pro_list[times] = p
            times_list[times] = times
            w2_drops_used_list[times] = glass.dropid

            logging.info("EW(w1_size=0.6) w1_pro=" + str(p) +" times: " + str(times) + 'done, w1_drops_used: ' + str(glass.w1_done_dropid) + ', w2_drops_used: '+ str(glass.dropid))
            times += 1

        res = pd.DataFrame({'w1_pro':w1pro_list, 
            'times':times_list, 
            'w1_drops_used':w1_drops_used_list,
            'w2_drops_used':w2_drops_used_list})
        res.to_csv(os.path.join(SIM_PATH, 'w1_pro选择/RSD反馈(0.6K_30)/feedback_EW_RSD(w1_size=0.6)_w1_pro=' + str(p) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        w1_avg_drops_list[avg_idx] = float(sum(w1_drops_used_list) / len(w1_drops_used_list))
        w2_avg_drops_list[avg_idx] = float(sum(w2_drops_used_list) / len(w2_drops_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'w1_pro': w1_pro_list, 
            'w1_avgs': w1_avg_drops_list,
            'w2_avgs': w2_avg_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'w1_pro选择/RSD反馈(0.6K_30)/feedback_EW_RSD(w1_size=0.6)_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')


# 不同per与译码开销的关系
per_list = [0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,0.125,0.15,0.175,0.2,0.225,0.25,0.275,0.3,0.325,0.35,0.375,0.4,0.425,0.45,0.475,0.5]
suffix_list = ['915.txt']
def test_LT_fountain_per():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_drops_list = [0]*len(per_list)
    avg_idx = 0

    for per in per_list:
        m = open(file_list[0], 'r').read()
        # 测试1000次
        tmp_per_list = [0]*100
        times_list = [0]*100
        drop_num_used_list = [0]*100

        times = 0
        K = 0
        while times < 100:
            fountain = Fountain(m, 1)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            while not glass.isDone():
                a_drop = fountain.droplet()       # send

                interval = round(1/per)
                if fountain.dropid % interval!=0:
                    glass.addDroplet(a_drop)          # recv
                # logging.info('+++++++++++++++++++++++++++++')
                # logging.info(glass.getString())

            tmp_per_list[times] = per
            times_list[times] = times
            drop_num_used_list[times] = glass.dropid

            logging.info("per=" + str(per) +" times: " + str(times) + 'done, receive_drop_used: ' + str(glass.dropid))
            times += 1

        # res = pd.DataFrame({'num_chunks':num_chunks_list, 
        #     'times':times_list, 
        #     'drop_num_used':drop_num_used_list})
        # res.to_csv(os.path.join(SIM_PATH, 'K' + '_'+ str(K) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_drops_list[avg_idx] = float(sum(drop_num_used_list) / len(drop_num_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'per': per_list, 
            'avgs':avg_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'PER对喷泉码的影响/RSD_LT_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

def test_ew_fountain_per():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_drops_list = [0]*len(per_list)
    avg_idx = 0

    for per in per_list:
        m = open(file_list[0], 'r').read()
        # 测试1000次
        tmp_per_list = [0]*100
        times_list = [0]*100
        drop_num_used_list = [0]*100

        times = 0
        K = 0
        while times < 100:
            fountain = EW_Fountain(m, 1)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            ew_drop = None
            while not glass.isDone():
                a_drop = fountain.droplet()       # send
                if a_drop.func_id==0:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=[], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)
                else:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=glass.process_history[a_drop.feedback_idx], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)

                interval = round(1/per)
                if fountain.dropid % interval!=0:
                    glass.addDroplet(ew_drop)          # recv

            tmp_per_list[times] = per
            times_list[times] = times
            drop_num_used_list[times] = glass.dropid

            logging.info("EW per=" + str(per) +" times: " + str(times) + 'done, receive_drop_used: ' + str(glass.dropid))
            times += 1

        # res = pd.DataFrame({'num_chunks':num_chunks_list, 
        #     'times':times_list, 
        #     'drop_num_used':drop_num_used_list})
        # res.to_csv(os.path.join(SIM_PATH, 'EW(0.6, 0.6)/RSD/no_feedback/EW_K' + '_'+ str(K) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_drops_list[avg_idx] = float(sum(drop_num_used_list) / len(drop_num_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'per': per_list, 
            'avgs':avg_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'PER对喷泉码的影响/RSD_EW_LT_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

def test_ew_feedback_fountain_per():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_send_drops_list = [0]*len(per_list)
    avg_recv_drops_list = [0]*len(per_list)
    avg_idx = 0
    avg_acknums_list = [0]*len(per_list)
    ack_idx = 0

    for per in per_list:
        m = open(file_list[0], 'r').read()
        # 测试次数
        max_times = 200
        tmp_per_list = [0]*max_times
        times_list = [0]*max_times
        send_drop_num_used_list = [0]*max_times
        recv_drop_num_used_list = [0]*max_times
        acknums_list = [0]*max_times

        times = 0
        K = 0
        while times < max_times:
            fountain = EW_Fountain(m, 1)
            K = fountain.num_chunks
            glass = Glass(fountain.num_chunks)
            ack_num = 0
            ew_drop = None
            send_drops = 0
            feedback_send_drops = 0
            w1_done_dropid = 0
            sender_get_process = False
            tmp_flag = False

            Y_N = ''
            while not glass.isDone():
                a_drop = fountain.droplet()       # send
                if a_drop.func_id==0:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=[], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)
                else:
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=glass.process_history[a_drop.feedback_idx], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)
                send_drops += 1

                pack_loss = [True, False]
                prob_loss = [per, 1-per]
                pack_loss_flag = np.random.choice(pack_loss, 1, False, prob_loss)[0]
                if pack_loss_flag==False:             # 丢包
                    glass.addDroplet(ew_drop)         # recv

                # w1done之后每30个包反馈（缩进）/每3s反馈（不缩进）
                n2 = 30
                if(glass.is_w1_done(0.6)):
                    # 获得反馈时进度
                    if tmp_flag==False:
                        w1_done_dropid = send_drops
                        tmp_flag = True
                    if (send_drops - w1_done_dropid) % n2 == 0:
                    # if (glass.dropid - glass.w1_done_dropid) % n2== 0:
                        glass.process = glass.getProcess()
                        glass.process_history.append(glass.process)
                        feedback_send_drops = send_drops
                        sender_get_process = True
                # 发送端延迟获得反馈
                if sender_get_process==True and (send_drops - feedback_send_drops == 18):
                    fountain.chunk_process = glass.process
                    fountain.all_at_once = True
                    fountain.feedback_idx = ack_num
                    ack_num += 1
                    sender_get_process = False

            if m==glass.getString():
                Y_N = 'Y'
            else:
                Y_N = 'N'

            tmp_per_list[times] = per
            times_list[times] = times
            send_drop_num_used_list[times] = fountain.dropid
            recv_drop_num_used_list[times] = glass.dropid
            acknums_list[times] = ack_num

            logging.info("feedback_EW_per=" + str(per) +" times: " + str(times) + 'done, receive_drop_used: ' + str(glass.dropid) + ' send:' + str(fountain.dropid) + ' ' + Y_N)
            times += 1

        # res = pd.DataFrame({'per':tmp_per_list, 
        #     'times':times_list, 
        #     'drop_num_used':drop_num_used_list})
        # res.to_csv(os.path.join(SIM_PATH, 'PER对喷泉码的影响/feedback_RSD_EW_per=' + '_'+ str(per) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_send_drops_list[avg_idx] = float(sum(send_drop_num_used_list) / len(send_drop_num_used_list))
        avg_recv_drops_list[avg_idx] = float(sum(recv_drop_num_used_list) / len(recv_drop_num_used_list))
        avg_idx += 1
        avg_acknums_list[ack_idx] = float(sum(acknums_list) / len(acknums_list))
        ack_idx += 1
    
    avg_res = pd.DataFrame({'per': per_list, 
            'avg_send_drops':avg_send_drops_list, 
            'avg_recv_drops':avg_recv_drops_list,
            'feedback_packet_avgs':avg_acknums_list})
    avg_res.to_csv(os.path.join(SIM_PATH, 'PER对喷泉码的影响/画吞吐量/(定时3s反馈K=500)feedback_RSD_EW_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

# w1译出时剩余未译出的块数
def test_ew_feedback_fountain_nums_left():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    m = open(file_list[0], 'r').read()
    # 测试次数
    max_times = 200
    times_list = [0]*max_times
    nums_left_list = [0]*max_times
    idx = 0

    times = 0
    K = 0
    while times < max_times:
        fountain = EW_Fountain(m, 1)
        K = fountain.num_chunks
        glass = Glass(fountain.num_chunks)
        ew_drop = None
        send_drops = 0
        w1_done_dropid = 0

        while not glass.isDone():
            a_drop = fountain.droplet()       # send
            if a_drop.func_id==0:
                ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=[], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)
            else:
                ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, process=glass.process_history[a_drop.feedback_idx], func_id = a_drop.func_id, feedback_idx = a_drop.feedback_idx)
            send_drops += 1

            glass.addDroplet(ew_drop)         # recv

            if(glass.is_w1_done(0.6)):
                # 获得反馈时进度
                glass.process = glass.getProcess()
                break
   
        logging.info(" times: " + str(times) + 'done, nums_left: ' + str(len(glass.process)))
        times += 1

        nums_left_list[idx] = len(glass.process)
        idx += 1

    avgs_nums_left = float(sum(nums_left_list) / len(nums_left_list))
    print('avgs_nums_left: ', avgs_nums_left)
    
    avg_res = pd.DataFrame({'nums_left': nums_left_list})
    avg_res.to_csv(os.path.join(SIM_PATH, '915个块的w1译出时剩余的块个数feedback_RSD_EW_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')



if __name__ == "__main__":
    # test_ew_fountain_K()
    # test_ew_feedback_fountain_K()
    # test_ew_w1pro_overhead()
    # test_feedback_ew_w1pro_overhead()

    # test_LT_fountain_per()
    # test_ew_fountain_per()
    # test_ew_feedback_fountain_per()
    test_ew_feedback_fountain_nums_left()
    pass

    

