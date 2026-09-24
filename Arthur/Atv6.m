clc
clear all
close all

%% Carrega imagens
imag1 = imread('girl_c.jpg'); 
imag2 = imread('house_c.jpg');
imag3 = imread('lena_c.jpg');

imag = imag2; %Troca de imagem

%% Filtros

h1 = [1 1 1;1 1 1;1 1 1]; %Passa-baixas
h2 = [-1 -1 -1; -1 8 -1; -1 -1 -1]; %Passa-altas
h3 = [-1 0 1; -1 0 1; -1 0 1]; %Prewitt vertical
h4 = [-1 -1 -1; 0 0 0; 1 1 1]; %Prewitt horizontal
h5 = [-1 0 1; -2 0 2; -1 0 1]; %Sobel vertical
h6 = [-1 -2 -1; 0 0 0; 1 2 1]; %Sobel horizontal
h7 = [5 5 5; -3 0 -3; -3 -3 -3]; %Kirsch
h8 = [1 -2 1; -2 4 -2; 1 -2 1]; %Laplaciano


%% Imagem
fig = figure(1);
subplot(1,2,1)
imshow(imag)    %Imagem original

imag=rgb2gray(imag); %Transforma imagem para grayscale
imag=double(imag)./255;
colormap(gray(256));

subplot(1,2,2)
imshow(imag); %Imagem Preto e Branco

truesize(fig)

%% FFT da imagem
imagfft = fftshift(fft2(imag));
fig = figure(2);
colormap(gray(256))
imagesc(log(abs(imagfft)+1))
title('FFT')
colorbar;

truesize(fig)

%% Imagem filtrada

fig = figure(3);
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

truesize(fig)

%% Butter Passa-Baixa
% Criação das Matrizes de Distância (Domínio da Frequência)
[M, N] = size(imag);
u = -M/2 : (M/2)-1;
v = -N/2 : (N/2)-1;
[V, U] = meshgrid(v, u);
D = sqrt(U.^2 + V.^2); % Distância do centro do espectro

% Parâmetros do filtro
D0 = 15; % Frequência de corte
n = 3; % Ordem do filtro de Butterworth

% Criação das Máscaras dos Filtros
H_ideal_Baixa = double(D <= D0); % Filtro Ideal (Corte abrupto)
H_butter_Baixa = 1 ./ (1 + (D ./ D0).^(2 * n));% Filtro de Butterworth (Corte suave)

fig = figure(4);
A=H_ideal_Baixa.*imagfft;
A = ifft2(A);
subplot(2,2,1)
colormap(gray(256))
imshow(A)
title('Passa-Baixa Ideal')

A=H_butter_Baixa.*imagfft;
A = ifft2(A);
subplot(2,2,2)
colormap(gray(256))
imshow(A)
title('Passa-Baixa Butter')

%% Butter Passa-Alta

H_ideal_Alta = 1 - H_ideal_Baixa;
H_butter_Alta = 1 - H_butter_Baixa;

A=H_ideal_Alta.*imagfft;
A = ifft2(A);
subplot(2,2,3)
colormap(gray(256))
imshow(A)
title('Passa-Alta ideal')

A=H_butter_Alta.*imagfft;
A = ifft2(A);
subplot(2,2,4)
colormap(gray(256))
imshow(A)
title('Passa-Alta Butter')
truesize(fig)

%% Gera a imagem com “blur”
h=(1/16)*[1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ];
imagBlur=filter2(h,imag);

fig = figure(5);
colormap(gray(256));
imshow(imagBlur);
title('Imagem original com "blur" na direcao horizontal');
truesize(fig);

%% Aplicando filtros
imagBlurfft = fftshift(fft2(imagBlur));

fig = figure(6);
A=H_ideal_Baixa.*imagBlurfft;
A = ifft2(A);
subplot(2,2,1)
colormap(gray(256))
imshow(A)
title('Passa-Baixa Ideal')

A=H_butter_Baixa.*imagBlurfft;
A = ifft2(A);
subplot(2,2,2)
colormap(gray(256))
imshow(A)
title('Passa-Baixa Butter')

A=H_ideal_Alta.*imagBlurfft;
A = ifft2(A);
subplot(2,2,3)
colormap(gray(256))
imshow(A)
title('Passa-Alta ideal')

A=H_butter_Alta.*imagBlurfft;
A = ifft2(A);
subplot(2,2,4)
colormap(gray(256))
imshow(A)
title('Passa-Alta Butter')

truesize(fig)
