import os, sys
import pywt
import numpy as np
#  import matlab.engine
import pickle as pkl
from matplotlib import pyplot as plt

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
LEAN_IMG = os.path.join(DOC_PATH, 'lena512.bmp')
OUT_BIN = os.path.join(DOC_PATH, 'out.bin')
LEAN_IMG_NEW = os.path.join(DOC_PATH, 'lena512_reconstruct.bmp')
PKL_IMG_ARRAY = os.path.join(DOC_PATH, 'img_array.pkl')

#  eng = matlab.engine.start_matlab()
#  eng.addpath(LIB_PATH)


def aa():
    #  img = eng.read_img(LEAN_IMG)
    #  img_array = np.array([list(ii) for ii in img])
    #  pkl.dump(img_array, open(PKL_IMG_ARRAY, 'wb'))
    img_array = pkl.load(open(PKL_IMG_ARRAY, 'rb'))
    wp = pywt.WaveletPacket2D(data=img_array, wavelet='bior4.4', maxlevel=9)

    #  py_dwt = pywt.wavedec2(img_array, 'bior4.4')

    return wp
def plot_wavelet():
    bior = pywt.Wavelet('bior4.4')
    [phi_d, psi_d, phi_r, psi_r, x] = bior.wavefun()

    plt.subplot(2, 2, 1)
    plt.plot(x, phi_d)
    plt.subplot(2, 2, 2)
    plt.plot(x, psi_d)
    plt.subplot(2, 2, 3)
    plt.plot(x, phi_r)
    plt.subplot(2, 2, 4)
    plt.plot(x, psi_r)
    plt.show()


if __name__ == '__main__':
    #  wp = aa()
    plot_wavelet()
