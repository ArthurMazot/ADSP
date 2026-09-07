%% Análise em Frequência de Sinais de Áudio - Parte II

%{
a) Carregar um arquivo de áudio (.wav) armazenando o vetor de
amostras em y e a taxa de amostragem em Fs usando a função
audioread.
%}

clc;
clear;
close all;

[y, Fs] = audioread('AURORA - Running With The Wolves.wav');

%{
b) Multiplicar o vetor por diferentes escalares e escutar com a função
sound.
%}

vet = 2*rand([length(y), 2]);
%sound(y.*vet, Fs);


%{
c) Modificar o parâmetro Fs na função sound(y, Fs_mod) e observar
as alterações no tom (pitch) e tempo.
%}
%sound(y, Fs/4); %Fs/4 deixa a musica ainda mais lenta e mais grave
%sound(y, Fs/2); %Fs/2 deixa a musica mais lenta e mais grave
%sound(y, Fs);   %Fs mantém a musica na velocidade e pitch originais
%sound(y, Fs*2); %Fs*2 deixa a musica mais rapida e mais aguda
%sound(y, Fs*4); %Fs*4 deixa a musica ainda mais rapida e mais aguda

%{
d) Utilizar a função flipud para inverter o vetor de áudio, escutar e
exportar o resultado com audiowrite.
%}

y_inv = flipud(y);

figure(5);
plot(y_inv);

%sound(y_inv, Fs);
audiowrite("AURORA - Running With The Wolves Flipped.wav", y_inv, Fs);

%{
Importar uma música estéreo que possua voz bem definida ao
centro.

Esta música: AURORA - Running With The Wolves
Possui dois canais (estéreo) e voz centralizada. 
Portanto continuará sendo usada.
%}

%{
f) Incluir uma verificação condicional (if/size) para garantir que o áudio
possui 2 canais. Caso contrário, interromper a execução com erro.
%}

if size(y, 2) ~= 2
    error("O arquivo de áudio não possui 2 canais.");
end

%{
g) Separar as colunas da matriz em canal esquerdo (L) 
e canal direito
(R).
%}
left = y(:,1);
right = y(:,2);

%{
h) Realizar a subtração R - L para obter a música sem voz
%}
SemVocal = right - left;

%{
i) Gerar uma janela de gráficos com 4 subplots (2x2): Original,
Esquerdo (L), Direito (R) e Sem Vocal (R-L).
%}
figure(6)

subplot(2,2,1)
plot(y)
title("Original")

subplot(2,2,2)
plot(left)
title("Esquerda")

subplot(2,2,3)
plot(right)
title("Direita")

subplot(2,2,4)
plot(SemVocal)
title("Sem Vocal (R-L)")

% J)
%sound(SemVocal, Fs)
audiowrite("AURORA - Running With The Wolves Sem Vocal.wav", SemVocal, Fs);

%{
Questão 1. O que ocorre com o tom (pitch) e com a duração do
áudio ao alterar a frequência de amostragem informada na função
sound? Explique a relação entre a taxa de amostragem e a
reprodução temporal.

Durante os testes, foi possível perceber um chiado, 
principalmente nas frequências mais altas. 
Que ocorre devido à alteração da taxa de reprodução do sinal, 
que modifica a forma como as amostras são reproduzidas. 
Portanto, a frequência de amostragem informada ao sound determina a 
velocidade temporal da reprodução: quanto maior a taxa 
utilizada em relação à original, mais rápido o áudio é reproduzido 
(o que reduz a duração e deixa o tom mais agudo), e quanto menor, 
mais lento (o que aumenta a duração e deixa o tom mais grave).
%}

%{
Questão 2. A função flipud altera o conteúdo espectral (as
frequências presentes) do sinal de áudio ou apenas a sequência
dos eventos no tempo? Justifique

A função flipud altera apenas a sequência dos eventos no tempo. 
Ela não muda o conteúdo espectral porque inverter o sinal no tempo 
(tocar de trás para frente) apenas altera a fase das frequências, 
mas mantém a mesma magnitude do espectro. Como as amostras originais 
continuam lá, as frequências presentes e a energia do sinal permanecem 
exatamente as mesmas, mudando apenas a ordem em que os sons acontecem.

%}

%{
Questão 3. Por que a subtração (R - L) atenua o vocal principal sem
remover completamente os instrumentos da música?

A subtração funciona porque a voz principal geralmente é gravada 
no "centro" da música, ou seja, ela tem exatamente o mesmo volume e 
intensidade nos canais esquerdo (L) e direito (R). 
Quando fazemos R - L, o que é igual nos dois lados se cancela (o vocal). 
Já os instrumentos não somem de vez porque eles costumam ser distribuídos 
de forma diferente entre as caixas (efeito estéreo), mas podem perder 
um pouco de volume se compartilharem frequências ou 
também estiverem centralizados.
%}