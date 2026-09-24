clc;
clear;
close all;

%{
1. Carregar uma das imagens e transformar em uma imagem em grayscale.
%}

X1=imread('girl_c.jpg'); 

fig = figure;

X=rgb2gray(X1); %Transforma imagem para grayscale 
imagem=double(X)./255; 

subplot(1, 2, 1);
imshow(X1);
title('Imagem original');

subplot(1, 2, 2);
colormap(gray(256)); 
imshow(imagem); %Visualiza imagem original
title('Imagem preto e branco');

truesize(fig);

%{
Verificar a transformada de Forier da imagem (ver função fft2 do MATLAB) e
viasualizar o espectro resultante.
%}



