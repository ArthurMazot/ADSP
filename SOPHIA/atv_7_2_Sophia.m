clear;
close all;

%{
1. Ler a imagem e convertê-la para tons de cinza (se necessário) e double
%}

I = imread('lena_c.jpg'); 

fig = figure(1);
subplot(2, 1, 1);
imshow(I); 
title('Imagem original');

if size(I, 3) == 3
    IrgbG = rgb2gray(I);
end
Idouble = im2double(IrgbG); % A DCT exige dados do tipo double ou single

subplot(2, 1, 2);
colormap(gray(256)); 
imshow(Idouble);
title('Imagem preto e branco');

truesize(fig);
%{
2. Definir o tamanho do bloco (8x8)
%}
tamanho_bloco = [8 8];

%{
3. Criar a função anônima que aplica a dct2 em cada bloco
O parâmetro 'b' representa uma estrutura que contém os dados do bloco em 'b.data'
%}

funcao_dct = @(b) dct2(b.data);

%{
4. Processar a imagem inteira bloco por bloco
%}

imagem_dct = blockproc(Idouble, tamanho_bloco, funcao_dct);

fig = figure(2);

subplot(2, 2, 1);
imshow(log(abs(imagem_dct) + 1), []);
title('Coeficientes DCT por Blocos');

funcao_idct = @(b) idct2(b.data);
imagem_idct = blockproc(imagem_dct,tamanho_bloco,funcao_idct);

subplot(2, 2, 2);
imshow(imagem_idct);
title('Resultado da inversa');

for i = 1:256
    for j = 1:256
       % if rem(i-1,8) == 0
        if imagem_dct(i,j) < 2
            imagem_dct(i,j) = 0;
        end
    end
end

%{
5. Visualizar o resultado aplicando o log para realçar os coeficientes
%}

subplot(2, 2, 3);
imshow(log(abs(imagem_dct) + 1), []);
title('Coeficientes DCT por Blocos após for');

funcao_idct = @(b) idct2(b.data);
imagem_idct = blockproc(imagem_dct,tamanho_bloco,funcao_idct);

subplot(2, 2, 4);
imshow(imagem_idct);
title('Resultado da inversa depois for');

truesize(fig);

