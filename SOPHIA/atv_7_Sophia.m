clear;
close all;
%{
1. Carregar uma imagem de tamanho 256x256 e converter para escala de cinza
(0 a 255).
%}
X1=imread('house_c.jpg'); 

X=rgb2gray(X1); %Transforma imagem para grayscale 
imag=double(X)./255; 

fig = figure(1);
subplot(1, 2, 1);
imshow(X1); 
title('Imagem original');

subplot(1, 2, 2);
colormap(gray(256)); 
imshow(imag);
title('Imagem preto e branco');
truesize(fig);

%{
2. Calcular a DCT 2D da imagem utilizando a função dct2 do MATLAB.
%}

imagt=dct2(imag);

figure();
colormap(gray(256)),imagesc(log(abs(imagt))),colorbar
title('Imagem após DCT2');

%{
3. Exibir o espectro de magnitude da DCT usando escala logarítmica
(log(1+|DCT|) ou log(|DCT|)) em uma janela gráfica com mapa de cores em
tons de cinza e barra de cores (colorbar).
%}

j=1;
A=zeros(256);
A(1:j,1:j)=fliplr(triu(ones(j)));

imagrt=imagt.*A;
iimagrt=idct2(imagrt);

figure(3);
imshow(iimagrt,256);
truesize;



