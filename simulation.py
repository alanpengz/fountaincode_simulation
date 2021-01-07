# _*_ coding=utf-8 _*_ 
from __future__ import print_function
import sys, os
sys.path.append('./lib')
from fountain_lib import EW_Fountain, EW_Droplet
from fountain_lib import Fountain, Glass
import numpy as np
import pandas as pd
import time
import logging
from math import ceil, log, log10
from tqdm import tqdm
import matplotlib.pyplot as plt
from dwt_lib import load_img
# from scipy.special import comb
import math
import pickle as pkl
# hxx = hpy()
# heap = hxx.heap()
# byrcs = hxx.heap().byrcs; 

plt.ion()
BASE_DIR = os.path.dirname(__file__)
LIB_PATH = os.path.join(BASE_DIR, 'lib')
DOC_PATH = os.path.join(BASE_DIR, 'doc')
SIM_PATH = os.path.join(BASE_DIR, 'simulation')
WHALE_IMG = os.path.join(DOC_PATH, 'whale_512.bmp')
WHALE_128_IMG = os.path.join(DOC_PATH, 'whale_128.bmp')
WHALE_128_JPG = os.path.join(DOC_PATH, 'whale_128.jpg')
WHALE_128_JPG_RS = os.path.join(DOC_PATH, 'whale_128_rs.jpg')

# def PSNR(img0, img1):
#     """
#     计算两个图像的PSNR值
#     img0 和 img1 的大小需要一样
#     """
#     Q = 255
#     mse = MSE_RGB(img0, img1)
#     psnr = 10 * math.log10(Q * Q / mse)
#     return psnr

# def MSE_RGB(img0, img1):
#     '''
#     计算两张图片的MSE,
#     img0 和 img1 的大小需要一样
#     '''
#     I0 = load_img(img0)
#     I1 = load_img(img1)
#     (width, height) = I0.size

#     mat_r0 = np.empty((width, height))
#     mat_g0 = np.empty((width, height))
#     mat_b0 = np.empty((width, height))

#     mat_r1 = np.empty((width, height))
#     mat_g1 = np.empty((width, height))
#     mat_b1 = np.empty((width, height))

#     for i in range(width):
#         for j in range(height):
#             [r0, g0, b0] = I0.getpixel((i, j))
#             mat_r0[i, j] = r0
#             mat_g0[i, j] = g0
#             mat_b0[i, j] = b0

#     for i in range(width):
#         for j in range(height):
#             [r1, g1, b1] = I1.getpixel((i, j))
#             mat_r1[i, j] = r1
#             mat_g1[i, j] = g1
#             mat_b1[i, j] = b1

#     temp_r = 0
#     for i in range(width):
#         for j in range(height):
#             mse = float((mat_r0[i, j] - mat_r1[i, j])**2)
#             temp_r += mse
#     mse_r = temp_r / (width * height)

#     temp_g = 0
#     for i in range(width):
#         for j in range(height):
#             mse = float((mat_g0[i, j] - mat_g1[i, j]) ** 2)
#             temp_g += mse
#     mse_g = temp_g / (width * height)

#     temp_b = 0
#     for i in range(width):
#         for j in range(height):
#             mse = float((mat_b0[i, j] - mat_b1[i, j]) ** 2)
#             temp_b += mse
#     mse_b = temp_b / (width * height)

#     mse = (mse_r + mse_g + mse_b) / 3
#     # rgb0 = np.array(I0).transpose(1, 2, 0).astype(float)
#     # rgb1 = np.array(I1).transpose(1, 2, 0).astype(float)
#     # mse = sum(sum(sum((rgb0 - rgb1) ** 2)))
#     return mse


def PSNR(img0, img1):
    """
    计算两个图像的PSNR值
    img0 和 img1 的大小需要一样
    """
    Q = 255
    mse = MSE_RGB(img0, img1)
    psnr = 10 * log10(Q * Q / mse)
    return psnr

def MSE_RGB(img0, img1):
    '''
    计算两张图片的MSE,
    img0 和 img1 的大小需要一样
    '''
    I0 = load_img(img0)
    I1 = load_img(img1)
    (width, height) = I0.size
    rgb0 = np.array(I0).transpose(1, 2, 0).astype(float)
    rgb1 = np.array(I1).transpose(1, 2, 0).astype(float)
    mse = sum(sum(sum((rgb0 - rgb1) ** 2))) / (width * height * 3)
    return mse

#  logging.basicConfig(level=logging.DEBUG)
m = ' ' * 32820 * 3
def sim_chunk_size():
    test_dir = os.path.join(SIM_PATH, 'sim_chunk_size')
    if not os.path.exists(test_dir):
        os.mkdir(test_dir)

    test_res_file = os.path.join(test_dir,time.asctime().replace(' ', '_').replace(':', '_')) + '.csv'
    # chunk_sizees = [int(ii) for ii in np.logspace(1.7, 4.99, 20)]
    chunk_sizees = range(100, 5050, 50)
#    chunk_sizees.reverse()
    code_rate= [0] * len(chunk_sizees)
    drops_num = [0] * len(chunk_sizees)
    per_list = [0] * len(chunk_sizees)
    i = 0
    loop_num = 100
    BER = 0.00001
    for size in tqdm(chunk_sizees):
        for j in tqdm(range(loop_num)):
            fountain = EW_Fountain(m, chunk_size=size, seed=255)
            glass = Glass(fountain.num_chunks)
            drop_id = 0
            PER = 1 - (1 - BER) ** (size * 8)
            while not glass.isDone():
                drop_id += 1
                a_drop = fountain.droplet()
                ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks)
                glass.addDroplet(ew_drop)
            code_rate[i] += size * drop_id / (1 - PER) 
            drops_num[i] += drop_id
            per_list[i] = PER
        i += 1
    code_rate = [float(ii) / (len(m) * loop_num) for ii in code_rate]
    drops_num = [float(ii) / loop_num for ii in drops_num]
    df_res = pd.DataFrame({
        "size":chunk_sizees, 
        "code_rate":code_rate, 
        'drops_num':drops_num,
        'loop_num':[loop_num for ii in chunk_sizees],
        'BER':[BER for ii in chunk_sizees],
        'PER':per_list})
    df_res.to_csv(test_res_file)
    return test_res_file
                
def sim_p1():
    test_dir = os.path.join(SIM_PATH, 'sim_p1')
    res_file = os.path.join(test_dir,time.asctime().replace(' ', '_').replace(':', '_')) + '.csv'
    step = 0.05
    floor = 0.3
    ceiling = 0.7
    p1_list = list(np.arange(floor, ceiling, step))
    p1_list.reverse()
    code_rate = [0] * len(p1_list)
    w1_size = 0.5
    w1_done = [0] * len(p1_list)
    w2_done = [0] * len(p1_list)
    per_list = [0] * len(p1_list)
    chunk_size = 255
    loop_num = 50
    chunk_num = ceil(len(m) / float(chunk_size))
    BER = 0.0001
    i = 0
    for p1 in tqdm(p1_list):
        for j in tqdm(range(loop_num)):
            fountain = EW_Fountain(m, chunk_size=chunk_size, w1_size=w1_size, w1_pro=p1)
            glass = Glass(fountain.num_chunks)
            drop_id = 0
            PER = 1 - (1 - BER) ** (chunk_size * 8)
            w1_done_t = 0
            while not glass.isDone():
                drop_id += 1
                a_drop = fountain.droplet()
                ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, w1_size, w1_pro=p1)
                glass.addDroplet(ew_drop)
                if glass.is_w1_done(w1_size) and w1_done_t == 0:
                    w1_done_t = drop_id
                del a_drop
                del ew_drop
            code_rate[i] += chunk_size * drop_id / (1 - PER)
            w1_done[i] += w1_done_t * chunk_size / (1 - PER)
            w2_done[i] += drop_id * chunk_size / (1 - PER)
            per_list[i] = PER
            del fountain
            del glass
        i += 1
    code_rate = [float(ii) / (len(m) * loop_num) for ii in code_rate]
    w1_done = [float(ii) / (len(m) * loop_num) for ii in w1_done]
    w2_done = [float(ii) / (len(m) * loop_num) for ii in w2_done]
    df_res = pd.DataFrame({
        "p1":p1_list, 
        "code_rate":code_rate, 
        'w1_done':w1_done,
        'w2_done':w2_done,
        'per':per_list,
        'loop_num':[loop_num for ii in p1_list],
        'chunk_size':[chunk_size for ii in p1_list],
        'chunk_num':[chunk_num for ii in p1_list],
        'w1_size':[w1_size for ii in p1_list]
        })
    df_res.to_csv(res_file)
    print(df_res)
    return res_file

def sim_diff_psnr():
    test_dir = os.path.join(SIM_PATH, 'sim_diff_psnr')
    if not os.path.exists(test_dir):
        os.mkdir(test_dir)
    res_file = os.path.join(test_dir,time.asctime().replace(' ', '_').replace(':', '_')) + '.csv'
    
    need_lest = 79
    packet_ceil = 631
    deli_rate = pkl.load(open(os.path.join(SIM_PATH, 'deil.pkl'), 'rb'))
    loop_num = 1000
    m = ' ' * need_lest
    p1_list = list(np.arange(0.1, 0.9, 0.1))
    w1_list = list(np.arange(0.1, 0.9, 0.1))
    res_size = len(p1_list) * len(w1_list)

    res_w1 = [0] * res_size
    for i in range(res_size):
        res_w1[i] = w1_list[int(i / len(p1_list))]
    res = pd.DataFrame({
        "w1":res_w1,
        'p1':p1_list * len(w1_list),
        # 'w1_done' : [0] * res_size,
        # "all_done": [0] * res_size
        })
    
    w1_done_tmp = [0] * res_size
    all_done_tmp = [0] * res_size
    i = 0
    for w1 in tqdm(w1_list):
        j = 0
        for p1 in tqdm(p1_list):
            all_done = 0
            res_index = i * len(p1_list) + j
            for loop in tqdm(range(loop_num)):
                fountain = EW_Fountain(m, chunk_size=1, w1_size=w1, w1_pro=p1)
                glass = Glass(fountain.num_chunks)
                w1_done = 0
                for drop_id in range(packet_ceil):
                    a_drop = fountain.droplet()
                    ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, w1, p1)
                    glass.addDroplet(ew_drop)
                    if glass.is_w1_done(w1) and w1_done == 0:
                        w1_done_tmp[res_index] += drop_id
                        w1_done = 1
                        # print("w1 done at {}".format(drop_id))
                    elif glass.isDone():
                        # print("all done at {}".format(drop_id))
                        all_done_tmp[res_index] += drop_id
                        break;
            w1_done_tmp[res_index] = w1_done_tmp[res_index] / float(loop_num) 
            all_done_tmp[res_index] = all_done_tmp[res_index] / float(loop_num) 
            j += 1
        i += 1    
    res['w1_done'] = w1_done_tmp
    res['all_done'] = all_done_tmp
    res = res[['w1', 'p1', 'w1_done', 'all_done']]
    print(res)
    res.to_csv(res_file)

def sim_ack_per():
    test_dir = os.path.join(SIM_PATH, "sim_ack_per")
    if not os.path.exists(test_dir):
        os.mkdir(test_dir)
    deli_rate = pkl.load(open(os.path.join(SIM_PATH, 'deil.pkl'), 'rb'))['1']
    per = [1 - ii for ii in deli_rate]
    print(per)
    packet_size = 78
    blank = '\0' * packet_size
    loop_num = 100
    psnr_list = [0] * len(per)
    psnr_count = [0] * len(per)

    df_file = os.path.join(test_dir, 'res_df.csv')        
    res_index = 0
    for p in tqdm(per):
        res_file = os.path.join(test_dir, str(p) + '_.bmp')
        for loop in tqdm(range(loop_num)):
            out_fd = open(res_file, 'w')
            img_raw_fd= open(WHALE_128_IMG, 'r')
            while True:
                read_tmp = img_raw_fd.read(packet_size)
                if read_tmp:
                    if not random_drop(p).next():
                        out_fd.write(read_tmp)
                    else:
                        out_fd.write(blank)
                else:    
                    break
            out_fd.close()
            img_raw_fd.close()    
            try:
                psnr_list[res_index] += PSNR(WHALE_128_IMG, res_file)
                psnr_count[res_index] += 1
            except:
                print('psnr error')
        res_index += 1        
    df = pd.DataFrame({
        'e2e_per':per,
        'PSNR':[psnr_list[ii] / (psnr_count[ii] + 0.0001) for ii in range(len(per))],
        'count':psnr_count,
        'loop_num':[loop_num]*len(per)
        })                
    print(df)
    df.to_csv(df_file)







def sim_compare():
    test_dir = os.path.join(SIM_PATH, "sim_compare")
    if not os.path.exists(test_dir):
        os.mkdir(test_dir)

    ber =np.arange(0.0041, 0.0142, 0.001)
    chunk_size = 50
    BER_step = 0.00001
    BER_ceil = 0.0005
    # BER_list = np.arange(BER_step, BER_ceil, BER_step)
    BER_list = ber
    PER_list = [1 - (1 - ii) ** (chunk_size * 8) for ii in BER_list]
    blank = '\0' * chunk_size
    loop_num = 100
    psnr_list = [0] * len(BER_list)
    psnr_count = [0] * len(BER_list)

    ll = 0
    res_file = os.path.join(test_dir, 'tmp') + '.bmp'
    # print(res_file)
    print(WHALE_IMG)
    for PER in tqdm(PER_list):
        for i in tqdm(range(loop_num)):
            # res_file = os.path.join(test_dir, str(PER)+"_"+str(i)) + '.bmp'
            out_fd = open(res_file, 'w')
            img_raw_fd= open(WHALE_IMG, 'r')
            while True:
                read_tmp = img_raw_fd.read(chunk_size)
                if read_tmp:
                    if not random_drop(PER).next():
                        out_fd.write(read_tmp)
                    else:
                        out_fd.write(blank)
                else:
                    break
            out_fd.close()    
            img_raw_fd.close()
            try:
                psnr_list[ll] += PSNR(WHALE_IMG, res_file)
                psnr_count[ll] += 1
            except:
                print('psnr error')
                pass
        ll += 1
    df = pd.DataFrame({
        'BER':BER_list,
        'PER':PER_list,
        'psnr':[psnr_list[ii] / (psnr_count[ii] + 0.00001) for ii in range(len(PER_list))],
        'psnr_count':psnr_count,
        })
   
    df.to_csv(os.path.join(test_dir, time.asctime().replace(' ', '_').replace(':', '_') + 'compare.csv'))
    print(df)

def sim_rs():
    test_dir = os.path.join(SIM_PATH, "sim_rs")
    if not os.path.exists(test_dir):
        os.mkdir(test_dir)

    chunk_size = 255
    ber =np.arange(0.0001, 0.015, 0.001)
    ser = [1 - (1-ii)**8 for ii in ber]
    rs_per = [rs_drop(ii) for ii in ser]
    per = [1 - (1 - ii)**(8 * 255) for ii in ber]
    psnr_list = [0] * len(ber)
    psnr_count = [0] * len(ber)

    blank = '\0' * chunk_size
    loop_num = 500
    res_file = os.path.join(test_dir, 'tmp') + '.bmp'
    jj = 0
    for PER in tqdm(rs_per):
        for i in tqdm(range(loop_num)):
            out_fd = open(res_file, 'w')
            img_raw_fd= open(WHALE_IMG, 'r')
            while True:
                read_tmp = img_raw_fd.read(chunk_size)
                if read_tmp:
                    if not random_drop(PER).next():
                        out_fd.write(read_tmp)
                    else:
                        out_fd.write(blank)
                else:
                    break
            out_fd.close()    
            img_raw_fd.close()
            try:
                psnr_list[jj] += PSNR(WHALE_IMG, res_file)
                psnr_count[jj] += 1
            except:
                print('psnr error')
                pass
        jj += 1
    df = pd.DataFrame({
        'BER':ber,
        'SER':ser,
        'PER':per,
        'RS_PER':rs_per,
        'psnr':[psnr_list[ii] / (psnr_count[ii]+0.001) for ii in range(len(ber))],
        'psnr_count':psnr_count,
        })
   
    df.to_csv(os.path.join(test_dir, time.asctime().replace(' ', '_').replace(':', '_') + 'rs_compare.csv'))
    print(df)

    rate_ceil = 10
    rate_step = 0.1
    code_rate = np.arange(1+rate_step, rate_ceil, rate_step)
    for rate in tqdm(code_rate):
        pass

def sim_ber():
    test_dir = os.path.join(SIM_PATH, 'sim_ber')
    if not os.path.exists(test_dir):
        os.mkdir(test_dir)

    chunk_size = 40
    loop_num = 5
    chunk_num = ceil(len(m) / float(chunk_size))
    
    p1 = 0.4
    ber =np.arange(0.0001, 0.015, 0.001)
    code_rate = [0] * len(ber)
    w1_size = 0.4
    w1_done = [0] * len(ber)
    w2_done = [0] * len(ber)
    per_list = [0] * len(ber)
    raw_data_size = len(m)
    i = 0
    for ber_ in tqdm(ber):
        print(heap)
        fountain = EW_Fountain(m, chunk_size=chunk_size, w1_size=w1_size, w1_pro=p1)
        for j in tqdm(range(loop_num)):
            glass = Glass(fountain.num_chunks)
            drop_id = 0
            PER = 1 - (1 - ber_) ** (chunk_size * 8)
            w1_done_t = 0
            while (not glass.isDone()):
                # print(drop_id * float(chunk_size) / len(m))
                drop_id += 1
                a_drop = fountain.droplet()
                ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, w1_size, w1_pro=p1)
                glass.addDroplet(ew_drop)
                if glass.is_w1_done(w1_size) and w1_done_t == 0:
                    w1_done_t = drop_id
                del a_drop
                del ew_drop
                if (drop_id * chunk_size / raw_data_size > 50):
                    print("_")
            code_rate[i] += chunk_size * drop_id / (1 - PER)
            w1_done[i] += w1_done_t * chunk_size / (1 - PER)
            w2_done[i] += drop_id * chunk_size / (1 - PER)
            per_list[i] = PER
            del glass
        del fountain
        i += 1
    code_rate = [float(ii) / (len(m) * loop_num) for ii in code_rate]
    w1_done = [float(ii) / (len(m) * loop_num) for ii in w1_done]
    w2_done = [float(ii) / (len(m) * loop_num) for ii in w2_done]
    df_res = pd.DataFrame({
        "ber":ber, 
        "code_rate":code_rate, 
        'w1_done':w1_done,
        'w2_done':w2_done,
        'per':[1 - (1 - ii)**(8 * chunk_size) for ii in ber],
        'loop_num':[loop_num for ii in ber],
        'chunk_size':[chunk_size for ii in ber],
        'p1':[p1 for ii in ber],
        'chunk_num':[chunk_num for ii in ber],
        'w1_size':[w1_size for ii in ber]
        })
    res_file = os.path.join(test_dir,time.asctime().replace(' ', '_').replace(':', '_')) + "_" + str(p1) + "_"+str(chunk_size)+ '.csv'
    df_res.to_csv(res_file)
    print(df_res)
    return res_file

def sim_hop():
    ber = 0.0001
    chunk_size = 50
    per = 1 - (1 - ber)**(chunk_size*8)
    loop_num = 5
    hop = range(1, 6)
    w1_size = 0.4
    p1 = 0.4
    for h in tqdm(hop):
        fountain = EW_Fountain(m, chunk_size=chunk_size, w1_size=w1_size, w1_pro=p1)
        for j in tqdm(range(loop_num)):
            drop_id = 0
            w1_done_t = 0
            glass = Glass(Fountain.num_chunks)
            while not glass.isDone():
                a_drop = fountain.droplet()
                ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks, w1_size, w1_pro=p1)
                glass.addDroplet(ew_drop)
                if glass.is_w1_done() and w1_done_t == 0:
                    w1_done_t = drop_id                    
                del a_drop
                del ew_drop



def rs_drop(ser):
    per = 0
    for i in range(0, 17):
        per += comb(255, i) * (ser ** i) * ((1 - ser)**(255-i))
    return 1 - per

def random_drop(per_=0.1):
    is_drop = [0, 1]
    prob = [1-per_, per_]
    while True:
        i = np.random.choice(is_drop, 1, False, prob)[0]
        yield i

def get_broken_image():
    packet_size = 78
    res_file = os.path.join(DOC_PATH,  'whale_broken_.bmp')
    img_raw_fd= open(WHALE_128_IMG, 'r')
    out_fd = open(res_file, 'w')
    p = 1 -  0.8368000000000001
    blank = '\0' * packet_size
    while True:
        read_tmp = img_raw_fd.read(packet_size)
        if read_tmp:
            if not random_drop(p).next():
                out_fd.write(read_tmp)
            else:
                out_fd.write(blank)
        else:    
            break


def sim_jpg_broken():
    def rs2jpg(rs_file):
        with open(rs_file, 'rb') as fin:
            rs_contain = fin.read()
        jpg_end = rs_contain.find('\xff\xd9') + 2
        with open(rs_file, 'wb') as fout:
            fout.write(rs_contain[:jpg_end])

    with open(WHALE_128_JPG_RS, 'rb') as fd:
        jpg_contain = fd.read()
    tmp_img = 'tmp.jpg'
    PER = [1.0, 0.9048, 0.5556, 0.47619999999999996, 0.4127, 0.381]
    PER = [1 - ii for ii in PER]
    loop_num = 1
    packet_size = 69
    packet_nums = int(ceil(len(jpg_contain) / float(packet_size)))
    for per in PER:
    # for i in range(loop_num):
        tmp_name = os.path.join(SIM_PATH, str(per)+tmp_img)
        print(tmp_name)
        fout = open(tmp_name, 'wb')
        drop_num = int(ceil(per * packet_nums))
        print('{} : {}'.format(packet_nums, drop_num))
        if per <= 6 / 63.0:
            print('psnr : {}'.format(PSNR(WHALE_128_JPG_RS, WHALE_128_IMG)))
            print()
        else:
            drop_series = np.random.choice(packet_nums-3, drop_num, replace=False)#不能选头和尾，减二
            drop_series = [ii + 2 for ii in drop_series]
            drop_mask = [1 if ii in drop_series else 0 for ii in range(packet_nums-1)]
            new_jpg_contain = ''
            for index_, drop_ in enumerate(drop_mask):
                if drop_:
                    new_jpg_contain += '\33'*packet_size
                else:
                    new_jpg_contain += jpg_contain[index_*packet_size : (index_+1)*packet_size]
            fout.write(new_jpg_contain)
            fout.close()
            rs2jpg(tmp_name)
            try:
                print('psnr : {}'.format(PSNR(tmp_name, WHALE_128_IMG)))
            except:
                print('psnr error')




def plot_x_y(df_file):
    df = pd.read_csv(df_file)
    y = df['code_rate']
    x = df['size']
    plt.figure()
    # plt.semilogx(x, y, lw=10)
    plt.plot(x, y)
    plt.xlabel('log(code block size)')
    plt.ylabel('code rate')
    plt.savefig(df_file + '.pdf')


if __name__ == '__main__':
    # print(heap)
    print("begin to simulation")
    if sys.argv[1] == 'tmp':
        print(PSNR('simulation/0.0952tmp.jpg', './doc/whale_128.bmp'))
        
    elif sys.argv[1] == 'chunk':
        df_file = sim_chunk_size()
        plot_x_y(df_file)
    elif sys.argv[1] == 'p1':
        sim_p1()
    elif sys.argv[1] == 'com':
        sim_compare()
    elif sys.argv[1] == 'rs':
        sim_rs()
    elif sys.argv[1] == 'ber':
        sim_ber()
    elif sys.argv[1] == 'psnr':
        sim_diff_psnr()
    elif sys.argv[1] == 'ack':
        sim_ack_per()
    elif sys.argv[1] == 'bro':
        get_broken_image()
    elif sys.argv[1] == 'jpg':
        sim_jpg_broken()
