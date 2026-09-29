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
imshow(imagem);
title('Imagem preto e branco');

truesize(fig);

%{
2. Verificar a transformada de Forier da imagem (ver função fft2 do MATLAB) e
viasualizar o espectro resultante.
%}

imgfft2 = fftshift(fft2(imagem));   %centraliza(Transformada de Fourier 2D)

espectro = log(1+abs(imgfft2));

fig = figure;
colormap(gray(256))
imagesc(espectro)
title('Espectro da transformada de Fourier')
colorbar;

truesize(fig)

%{
3. Na imagem, aplicar filtragens no domínio espacial utilizando cada uma das
mascaras apresentadas no material do moodle (ver função filter2 do MATLAB).
Para cada caso, visualizar simultaneamente a imagem original e a imagem
filtrada, avaliando o efeito resultante, em cada caso.
%}

%Filtro espacial Passa-Baixas
h1 = [1 1 1; 1 1 1; 1 1 1];
A1 = filter2(h1,imagem);

%Filtro espacial Passa-Altas
h2 = [-1 -1 -1; -1  8 -1; -1 -1 -1];
A2 = filter2(h2,imagem);

%Prewitt para bordas verticais
h3 = [-1 0 1; -1 0 1; -1 0 1];
A3 = filter2(h3,imagem);

%Prewitt para bordas horizontais
h4 = [-1 -1 -1; 0  0  0; 1  1  1];
A4 = filter2(h4,imagem);

%Sobel para bordas verticais
h5 = [-1 0 1; -2 0 2; -1 0 1];
A5 = filter2(h5,imagem);

%Sobel para bordas horizontais
h6 = [-1 -2 -1; 0  0  0; 1  2  1];
A6 = filter2(h6,imagem);

%Kirsch
h7 = [ 5  5  5; -3  0 -3; -3 -3 -3];
A7 = filter2(h7,imagem);

%Laplaciano
h8 = [ 1 -2  1; -2  4 -2; 1 -2  1];
A8 = filter2(h8,imagem);

%Imagem com todos os filtros
fig = figure;

subplot(3,3,1)
imshow(imagem)
colormap(gray(256));
title('Original')

subplot(3,3,2)
imshow(A1,[])
title('Passa-Baixas')

subplot(3,3,3)
imshow(A2,[])
title('Passa-Altas')

subplot(3,3,4)
imshow(A3,[])
title('Prewitt - Vertical')

subplot(3,3,5)
imshow(A4,[])
title('Prewitt - Horizontal')

subplot(3,3,6)
imshow(A5,[])
title('Sobel - Vertical')

subplot(3,3,7)
imshow(A6,[])
title('Sobel - Horizontal')

subplot(3,3,8)
imshow(A7,[])
title('Kirsch')

subplot(3,3,9)
imshow(A8,[])
title('Laplaciano')
