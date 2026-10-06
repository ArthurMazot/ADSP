clc
clear all
close all

%% Imagens

imag1 = imread('girl_c.jpg');
imag2 = imread('house_c.jpg');
imag3 = imread('lena_c.jpg');

I = imag2;

%% Script
% 1. Ler a imagem e convertê-la para tons de cinza (se necessário) e double 
if size(I, 3) == 3
    I = rgb2gray(I);
end
I = im2double(I); % A DCT exige dados do tipo double ou single

% 2. Definir o tamanho do bloco (8x8)
tamanho_bloco = [4 4];

% 3. Criar a função anônima que aplica a dct2 em cada bloco
% O parâmetro 'b' representa uma estrutura que contém os dados do bloco em 'b.data'
funcao_dct = @(b) dct2(b.data);

% 4. Processar a imagem inteira bloco por bloco
imagem_dct = blockproc(I, tamanho_bloco, funcao_dct);

for i = 1:256
   for j = 1:256
       if imagem_dct(i, j) > 2.5
           imagem_dct(i, j) = 0;
       end
   end
end


% 5. Visualizar o resultado aplicando o log para realçar os coeficientes
figure(1);
imshow(log(abs(imagem_dct) + 1), []);
title('Coeficientes DCT por Blocos');

funcao_idct = @(b) idct2(b.data);
imagem_idct = blockproc(imagem_dct, tamanho_bloco, funcao_idct);

figure(2)
imshow(imagem_idct)

figure(3)
imshow(I)