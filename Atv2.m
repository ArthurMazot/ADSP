clc
clear all
close all

%% A)
ny = 0:14; %Tamanho da convolução
na = 0:7;  %Tamanho do sinal A
nb = 0:7;  %Tamanho do sinal A
a = [1 2 3 4 5 6 7 8]; %Sinal A
b = [1 1 1 1 1 1 1 1]; %Sinal B

y = conv(a, b); %Convolução

figure(1)
subplot(3,1,1) %3 linhas, 1 coluna, mexendo no primeiro grafico
stem(na, a)
title('sinal A')

subplot(3,1,2)
stem(nb, b)
title('sinal B')

subplot(3,1,3)
stem(ny, y)
title('Convolução entre A e B')

%% B)
%Equação tirada da atividade
%y[n] + 1/3*y[n-1] = x[n] + 1/2*x[n-1]

%Transformada Z
%Y(Z)*(1 + 1/3*z^-1) = X(Z)*(1 + 1/2*z^-1)

%Função de Transferencia
%H(Z) = Y(Z)/X(Z) = (1+1/2*z^-1)/(1 + 1/3*z^-1)

num = [1 1/2]; %Numerador H(Z)
den = [1 1/3]; %Denominador H(Z)

%inp: numerador, denominador, quantas amostras serão simuladas
%out: resposta ao impulso, vetor de amostras [0, 1, 2, ...]
[H, T] = impz(num, den, 10);

figure(2)
stem(T,H);
title('Resposta ao impulso')

%% C)

w = 0.05*pi; %Omega
n = 0:100;   %Vetor de tempo
xn = 5*exp(1i*w*n); %Função da atividade

figure(3)
hold on
plot(n, real(xn), 'b') %Plot da parte real de xt em azul
plot(n, imag(xn), 'r--') %Plot da parte imaginaria de xt em vermelho com a linha traçada
legend('Real', 'Imaginária') %Coloca a legende para cada curva
title('Real / Imaginária')

figure(4)
subplot(2,1,1)
plot(n, abs(xn))
title('Modulo')

subplot(2,1,2)
plot(n, angle(xn))
title('Fase')

%% D)
%exatemente a mesma coisa só muda o xn
r = 0.95;
xn = 5*(r.^n).*exp(1i*w*n); %Função da atividade

figure(5)
hold on
plot(n, real(xn), 'b') %Plot da parte real de xt em azul
plot(n, imag(xn), 'r--') %Plot da parte imaginaria de xt em vermelho com a linha traçada
legend('Real', 'Imaginária') %Coloca a legende para cada curva
title('Real / Imaginária')

figure(6)
subplot(2,1,1)
plot(n, abs(xn))
title('Modulo')

subplot(2,1,2)
plot(n, angle(xn))
title('Fase')
