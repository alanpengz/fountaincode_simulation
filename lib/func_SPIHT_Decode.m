function MSE  = func_SPIHT_Decode(S, img_enc, img_out, infilename);

Orig_I = double(imread(infilename));
[nRow, nColumn] = size(Orig_I);

type = 'bior4.4';
[Lo_D,Hi_D,Lo_R,Hi_R] = wfilters(type);
level = 9.0;
outfilename = img_out;

img_dec = func_SPIHT_Dec(img_enc);
fprintf('done!\n');
fprintf('-----------   Wavelet Reconstruction   ----------------\n');
img_spiht = func_InvDWT(img_dec, S, Lo_R, Hi_R, level);
fprintf('done!\n');
fprintf('-----------   PSNR analysis   ----------------\n');
imwrite(img_spiht, gray(256), outfilename, 'bmp');
Q = 255;
MSE = sum(sum((img_spiht-Orig_I).^2))/nRow / nColumn;
fprintf('The psnr performance is %.2f dB\n', 10*log10(Q*Q/MSE));
