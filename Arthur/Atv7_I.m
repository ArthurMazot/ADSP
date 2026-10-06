clc
clear all
close all

%% Carrega imagens
imag1 = imread('girl_c.jpg'); 
imag2 = imread('house_c.jpg');
imag3 = imread('lena_c.jpg');
        
imag = imag3; %Troca de imagem

%% Imagem
%1)
imag=rgb2gray(imag); %Transforma imagem para grayscale
imag=double(imag)./255;
colormap(gray(256));

%% DCT

%2)
imagDCT = dct2(imag);

%3)
figure(1)
colormap(gray(256));
imagesc(log(abs(imagDCT)));
colormap(jet);
colorbar;

%4) As partes de maior amplitude (Mais claras no grafico), ficam
%principalmente no canto superior esquerdo. Que é a região que possui mais
%informação da imagem

%% Mascaramento

valores = [1, 2, 4, 8, 16, 32, 64, 128];

for i = 1:8
    %5 e 6)
    j = valores(i);
    A=zeros(256);
    A(1:j,1:j)=fliplr(triu(ones(j)));
    
    %7)
    imagrt=imagDCT.*A;
    iimagrt=idct2(imagrt);
    figure(1+i);
    imshow(iimagrt);
    truesize;
    
    % 8) Apartir de j = 64 ou j = 128 dependendo da imagem. A porcentagem
    % do coeficientes se da por j*(j+1)/131.0720
    coeficiente = j*(j+1)/131072;
    fprintf('J = %d: %f%%\n', j, coeficiente*100)
end

