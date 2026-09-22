clc
clear all
close all

%% Carrega imagens
imag1 = imread('girl_c.jpg'); 
imag2 = imread('house_c.jpg');
imag3 = imread('lena_c.jpg');

%% Filtros

h1 = [1 1 1;1 1 1;1 1 1]; %Passa-baixas
h2 = [-1 -1 -1; -1 8 -1; -1 -1 -1]; %Passa-altas
h3 = [-1 0 1; -1 0 1; -1 0 1]; %Prewitt vertical
h4 = [-1 -1 -1; 0 0 0; 1 1 1]; %Prewitt horizontal
h5 = [-1 0 1; -2 0 2; -1 0 1]; %Sobel vertical
h6 = [-1 -2 -1; 0 0 0; 1 2 1]; %Sobel horizontal
h7 = [5 5 5; -3 0 -3; -3 -3 -3]; %Kirsch
h8 = [1 -2 1; -2 4 -2; 1 -2 1]; %Laplaciano


%% imagem girl_c
figure(1)
imag=rgb2gray(imag1); %Transforma imagem para grayscale
imag1Wb=double(imag)./255;
colormap(gray(256));

subplot(3,2,1)
imshow(imag1)

subplot(3,2,2)
imshow(imag1Wb); %Visualiza imagem original

imag1fft = fftshift(fft2(imag1Wb));
figure(2)
colormap(gray(256))
imagesc(log(abs(imag1fft)+1))
title('FFT (girl c.jpf)')
colorbar;

%% imagem house_c
figure(1)
imag=rgb2gray(imag2); %Transforma imagem para grayscale
imag2Wb=double(imag)./255;
colormap(gray(256));

subplot(3,2,3)
imshow(imag2)

subplot(3,2,4)
imshow(imag2Wb); %Visualiza imagem original

imag2fft = fftshift(fft2(imag2Wb));
figure(3)
colormap(gray(256))
imagesc(log(abs(imag2fft)+1))
title('FFT (house c.jpf)')
colorbar;

%% imagem lena_c
figure(1)
imag=rgb2gray(imag3); %Transforma imagem para grayscale
imag3Wb=double(imag)./255;
colormap(gray(256));

subplot(3,2,5)
imshow(imag3)

subplot(3,2,6)
imshow(imag3Wb); %Visualiza imagem original

imag3fft = fftshift(fft2(imag3Wb));
figure(4)
colormap(gray(256))
imagesc(log(abs(imag3fft)+1))
title('FFT (lena c.jpf)')
colorbar;

%% Imagem filtrada

imag = imag2Wb; %Troca de imagem

figure(5)
subplot(3,3,5)
imshow(imag)
title('Original')


subplot(3,3,1)
A=filter2(h1,imag); %Efetua a filtragem com a máscara definida em h
colormap(gray(256));
imshow(A); %Visualiza imagem filtrada
title('Passa-Baixa')


subplot(3,3,2)
A=filter2(h2,imag); %Efetua a filtragem com a máscara definida em h
colormap(gray(256));
imshow(A); %Visualiza imagem filtrada
title('Passa-Alta')


subplot(3,3,3)
A=filter2(h3,imag); %Efetua a filtragem com a máscara definida em h
colormap(gray(256));
imshow(A); %Visualiza imagem filtrada
title('Prewitt vertical')


subplot(3,3,4)
A=filter2(h4,imag); %Efetua a filtragem com a máscara definida em h
colormap(gray(256));
imshow(A); %Visualiza imagem filtrada
title('Prewitt horizontal')


subplot(3,3,6)
A=filter2(h5,imag); %Efetua a filtragem com a máscara definida em h
colormap(gray(256));
imshow(A); %Visualiza imagem filtrada
title('Sobel vertical')


subplot(3,3,7)
A=filter2(h6,imag); %Efetua a filtragem com a máscara definida em h
colormap(gray(256));
imshow(A); %Visualiza imagem filtrada
title('Sobel horizontal')


subplot(3,3,8)
A=filter2(h7,imag); %Efetua a filtragem com a máscara definida em h
colormap(gray(256));
imshow(A); %Visualiza imagem filtrada
title('Kirsch')


subplot(3,3,9)
A=filter2(h8,imag); %Efetua a filtragem com a máscara definida em h
colormap(gray(256));
imshow(A); %Visualiza imagem filtrada
title('Laplaciano')