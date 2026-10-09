clear;
close all;

%{
1. Carregar uma imagem de tamanho 256x256 e 
converter para escala de cinza(0 a 255).
%}

X1=imread('lena_c.jpg'); 

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

%{
3. Exibir o espectro de magnitude da DCT usando escala logarítmica
(log(1+|DCT|) ou log(|DCT|)) em uma janela gráfica com mapa de cores em
tons de cinza e barra de cores (colorbar).
%}

figure(2);
colormap(gray(256));
imagesc(log(1+abs(imagt)));
colorbar;
title('Imagem após DCT2');

%{
5. Desenvolver uma função em MATLAB que construa a matriz de máscara A de
dimensão 256x256 para um determinado valor j.

6. Utilizar as funções zeros, ones, triu e fliplr.

7. Filtrar os coeficientes da DCT com a máscara zonal para diferentes
valores de j e reconstruir a imagem usando a IDCT 2D.
%}

valores=[1,2,4,8,16,32,64,128];

fig = figure(3);

for i=1:length(valores)

    j=valores(i);

    A=zeros(256);
    A(1:j,1:j)=fliplr(triu(ones(j)));

    imagrt=imagt.*A;
    iimagrt=idct2(imagrt);

    subplot(2,4,i);
    imshow(iimagrt,[]);
    title(['Imagem reconstruída para j = ',num2str(j)]);
end

truesize(fig);
