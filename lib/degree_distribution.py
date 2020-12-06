# _*_ coding=utf-8 _*_
from __future__ import print_function, division                                           
import random                                                                   
from math import ceil, log
import numpy as np
# import matplotlib.pyplot as plt

# plt.ion()
def soliton(N, seed):                                                           
    prng = random.Random()                                                        
    prng.seed(seed)                                                                  
    while 1:                                                                         
        x = random.random() # Uniform values in [0, 1)                                 
        i = int(ceil(1/x))       # Modified soliton distribution                            
        yield i if i <= N else 1 # Correct extreme values to 1                         

def my_soliton(K, seed=random.randint(0, 2 ** 32 - 1)):
    # 理想弧波函数
    d = [ii + 1 for ii in range(K)]
    d_f = [1.0 / K if ii == 1 else 1 / (ii * (ii - 1)) for ii in d]
    print(is_show)
    #  f = plt.figure()
    #  plt.bar(d, d_f)
    #  plt.show()
    while 1:
        i = np.random.choice(d, 1, False, d_f)[0]
        yield i
def windows_selection(p=0.7):
    '''以概率[{p:0, 1-p:1}返回选择的窗口'''
    d = [0, 1]
    w_f = [p, 1-p]
    while True:
        i = np.random.choice(d, 1, False, w_f)[0]
        yield i


def wrong_windows_selection(N=10, p=0.7, w1_size=3):
    '''以概率[{p:0, 1-p:1}返回选择的窗口'''
    num_chunks = N
    d = [ii+1 for ii in range(num_chunks)]
    print(d)
    w2_size = len(d) - w1_size
    print('w1_size: ', w1_size )
    print('w2_size: ', w2_size )

    w1_f = [p / w1_size for ii in range(int(w1_size))]
    w2_f = [(1-p) / w2_size for ii in range(int(w2_size))]
    w_f = w1_f + w2_f
    print(sum(w1_f))
    print(sum(w2_f))
    print(sum(w_f))
    print('w1_f: ', w1_f)
    print('w2_f: ', w2_f)
    print('w_f: ', w_f)

    while True:
        i = np.random.choice(d, 1, False, w_f)[0]
        yield i

def my_robust_soliton(K, c = 0.033, delta = 0.4, seed=random.randint(0, 2 ** 32 - 1)):
    # 鲁棒理想弧波函数
    d = [ii + 1 for ii in range(K)]
    soliton_d_f = [1.0 / K if ii == 1 else 1 / (ii * (ii - 1)) for ii in d]
    S = c * log(K / delta) * (K ** 0.5)
    interval_0 = [ii + 1 for ii in list(range(int(K / S) - 1))]
    interval_1 = [int(K / S)]
    print("knot", int(K / S))
    tau = [S / (K * dd) if dd in interval_0 
            else S / K * log(S / delta) if dd in interval_1
            else 0 for dd in d]

    Z = sum([soliton_d_f[ii] + tau[ii] for ii in range(K)])

    u_d_f = [(soliton_d_f[ii] + tau[ii]) / Z for ii in range(K)]
    #  f = plt.figure()
    #  plt.bar(d, u_d_f)
    #  plt.show()
    while 1 :
        i = np.random.choice(d, 1, False, u_d_f)[0]
        yield i

def main():
    N = 2
    T = 10 ** 5 # Number of trials                                                   
    #  s = soliton(N, seed = soliton(N, random.randint(0, 2 ** 32 - 1))) # soliton generator
    #  s = soliton(N, random.randint(0, 2 ** 32 - 1)) # soliton generator
    #  s = my_soliton(N)
    # s = my_robust_soliton(N)
    # s = wrong_windows_selection(N)
    s = windows_selection()
    f = [0]*N                       # frequency counter                              
    for j in range(T):                                                               
        i = next(s)                                                                    
        f[i-1] += 1                                                                    

    print("k\tFreq.\tExpected Prob\tObserved Prob\n");                               

    print("{:d}\t{:d}\t{:f}\t{:f}".format(1, f[0], 1/N, f[0]/T))                     
    for k in range(2, N+1):                                                          
        print("{:d}\t{:d}\t{:f}\t{:f}".format(k, f[k-1], 1/(k*(k-1)), f[k-1]/T))
    print(sum([f[ii] / T for ii in range(N)]))        


if __name__ == '__main__':                                                         
    # my_robust_soliton(100)
    # my_soliton(100)
    main()
    pass

