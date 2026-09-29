clc;
clear;
close all;

%{
1. Carregar uma das imagens e transformar em uma imagem em grayscale.
%}

X1 = imread('girl_c.jpg');

fig = figure(1);
X = rgb2gray(X1); %Transforma imagem para grayscale
imagem = double(X)./255;

subplot(1,2,1);
imshow(X1);
title('Imagem original');

subplot(1,2,2);
colormap(gray(256));
imshow(imagem); 
title('Imagem preto e branco');

truesize(fig);


%{
2. Obter o espectro de Fourier da imagem usando fft2 e centralizá-lo com fftshift.
%}

imgfft2 = fftshift(fft2(imagem));  %centraliza(Transformada de Fourier 2D)
espectro = log(1+abs(imgfft2));

fig = figure(2);
colormap(gray(256));
imagesc(espectro)
title('Espectro da transformada de Fourier')
colorbar;

truesize(fig)

%{
3. Criar uma máscara de Filtro Passa-Baixa Ideal e outra de Filtro Passa-Baixa de
Butterworth (com ordem n=2).
%}

% Criação das Matrizes de Distância (Domínio da Frequência)
[M, N] = size(imagem);
u = -M/2 : (M/2)-1;
v = -N/2 : (N/2)-1;
[V, U] = meshgrid(v, u);
D = sqrt(U.^2 + V.^2); % Distância do centro do espectro

% Parâmetros do filtro
D0 = 50; % Frequência de corte
n = 2; % Ordem do filtro de Butterworth

% Criação das Máscaras dos Filtros

% Filtro Ideal (Corte abrupto)
H_ideal = double(D <= D0);

% Filtro de Butterworth (Corte suave)
H_butter = 1 ./ (1 + (D ./ D0).^(2 * n));

%{
4. Realizar a filtragem com ambas as máscaras e frequência de corte (D0=50).
(produto da transformada de Fourier da Imagem com a mascara dos filtros).
%}

F_ideal = H_ideal.*imgfft2;
F_butter = H_butter.*imgfft2;


%{
5. Calcular a transformada inversa de Fourier (ifft2) e comparar os resultados obtidos
em cada caso.
%}

A_ideal = ifft2(ifftshift(F_ideal)); % Desfaz a centralização antes da transformada inversa
A_butter = ifft2(ifftshift(F_butter));


fig = figure(3);

subplot(1,3,1)
colormap(gray(256))
imshow(imagem)
title('Imagem original')

subplot(1,3,2)
imshow(A_ideal)
title('Passa-Baixa Ideal')

subplot(1,3,3)
imshow(A_butter)
title('Passa-Baixa Butterworth')

truesize(fig)

%{
6. Repetir para o filtro de Butterworth passa-altas (1 – Hpb(w)).
%}

% Criação das máscaras Passa-Altas
H_ideal_Alta = 1 - H_ideal;
H_butter_Alta = 1 - H_butter;

% Máscaras na transformada da imagem
F_ideal_Alta = H_ideal_Alta.*imgfft2;
F_butter_Alta = H_butter_Alta.*imgfft2;

% Desfaz a centralização antes da transformada inversa
A_ideal_Alta = ifft2(ifftshift(F_ideal_Alta));
A_butter_Alta = ifft2(ifftshift(F_butter_Alta));


fig = figure(4);

subplot(1,3,1)
colormap(gray(256))
imshow(imagem)
title('Imagem original')

subplot(1,3,2)
imshow(A_ideal_Alta,[])
title('Passa-Alta Ideal')

subplot(1,3,3)
imshow(A_butter_Alta,[])
title('Passa-Alta Butterworth')

truesize(fig)

%{
7. Alterar a ordem e a frequência de corte do filtro, no mínimo para outros 3 valores,
e repetir os itens 1 a 6. Verificar os efeitos que estas alterações produz na imagem
filtrada.
%}

% Valores de Fc e ordem para os três testes
D0_teste = [25 75 100];
n_teste = [1 3 4];

fig = figure(5);

for i = 1:3
    D0 = D0_teste(i);  % Parâmetros teste
    n = n_teste(i);

    H_butter = 1 ./ (1 + (D ./ D0).^(2 * n));  % Filtro de Butterworth (Corte suave)

    H_butter_Alta = 1 - H_butter;

    % Máscaras
    F_butter = H_butter.*imgfft2;
    F_butter_Alta = H_butter_Alta.*imgfft2;

    A_butter = ifft2(ifftshift(F_butter)); % Transformada inversa
    A_butter_Alta = ifft2(ifftshift(F_butter_Alta));

    subplot(2,3,i) % Passa-Baixa
    colormap(gray(256))
    imshow(A_butter)
    title(['PB: D0=',num2str(D0),' n=',num2str(n)])

    subplot(2,3,i+3) % Passa-Alta
    imshow(A_butter_Alta,[])
    title(['PA: D0=',num2str(D0),' n=',num2str(n)])

end

truesize(fig)


%{
8. Gerar uma imagem com “blur” na direção horizontal.
%}

h=(1/16)*[1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ];
A=filter2(h,imagem);
figure;
colormap(gray(256));
imshow(A);
title('Imagem original com "blur" na direcao horizontal');
truesize;

%{
9. Filtrar utilizando as máscaras do filtro ideal e de Butterworth. Verificar os
resultados obtidos.
%}

Afft = fftshift(fft2(A)); % TF da imagem com blur

% Transformada inversa
A_ideal_blur = ifft2(ifftshift(H_ideal.*Afft));
A_butter_blur = ifft2(ifftshift(H_butter.*Afft));
A_ideal_Alta_blur = ifft2(ifftshift(H_ideal_Alta.*Afft));
A_butter_Alta_blur = ifft2(ifftshift(H_butter_Alta.*Afft));

fig = figure(6);

subplot(2,2,1)
colormap(gray(256))
imshow(A_ideal_blur)
title('Passa-Baixa Ideal')

subplot(2,2,2)
imshow(A_butter_blur)
title('Passa-Baixa Butterworth')

subplot(2,2,3)
imshow(A_ideal_Alta_blur,[])
title('Passa-Alta Ideal')

subplot(2,2,4)
imshow(A_butter_Alta_blur,[])
title('Passa-Alta Butterworth')

truesize(fig)


%{
10. Alterar a frequência de corte e a ordem, visando atenuar o efeito do “blur”.
Verificar os resultados obtidos.
%}

% Efeito sobre a imagem com blur
D0_teste = [25 50 75];
n_teste = [1 2 3];

fig = figure(7);

for i = 1:3
    D0 = D0_teste(i); %Parâmetros teste
    n = n_teste(i);

    % Filtro de Butterworth (Corte suave)
    H_butter = 1 ./ (1 + (D ./ D0).^(2 * n));

    H_butter_Alta = 1 - H_butter;
    F_butter_Alta_blur = H_butter_Alta.*Afft; % Filtragem com Blur

    % Transformada inversa
    A_butter_Alta_blur = ifft2(ifftshift(F_butter_Alta_blur));

    subplot(1,3,i)
    colormap(gray(256))
    imshow(A_butter_Alta_blur,[])
    title(['D0=',num2str(D0),' n=',num2str(n)])

end

truesize(fig)
