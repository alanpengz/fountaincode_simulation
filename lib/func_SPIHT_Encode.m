function img_enc = func_SPIHT_Encode(img_file)
% Matlab implementation of SPIHT (without Arithmatic coding stage)
%
% Main function 
%
% input:    Orig_I : the original image.
%           rate : bits per pixel
% output:   img_spiht 
%
fprintf('-----------   Welcome to SPIHT Matlab Demo!   ----------------\n');
fprintf('-----------   Load Image   ----------------\n');
doc_dir = strcat(pwd(), '/doc/');
% infilename = strcat(doc_dir, 'lena512.bmp');
infilename = img_file
% outfilename = strcat(doc_dir, 'lena512_reconstruct.bmp');
Orig_I = double(imread(infilename));
rate = 1;
OrigSize = size(Orig_I, 1);
max_bits = floor(rate * OrigSize^2);
OutSize = OrigSize;
image_spiht = zeros(size(Orig_I));
[nRow, nColumn] = size(Orig_I);
fprintf('done!\n');
fprintf('-----------   Wavelet Decomposition   ----------------\n');
n = size(Orig_I,1);
n_log = log2(n); 
level = n_log;
% wavelet decomposition level can be defined by users manually.
type = 'bior4.4';
[Lo_D,Hi_D,Lo_R,Hi_R] = wfilters(type);
[I_W, S] = func_DWT(Orig_I, level, Lo_D, Hi_D);
fprintf('done!\n');
fprintf('-----------   Encoding   ----------------\n');
img_enc = func_MySPIHT_Enc(I_W, max_bits, nRow*nColumn, level);   
fprintf('done!\n');
