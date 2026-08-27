clc
clear all
close all

[x, fa] = audioread('Bagatelle-no.-25-__Für-Elise___-WoO-59.wav');

%% A)

n = pow2(nextpow2(length(x(:,1)))); %Corrige para a próxima potencia de 2

y = fft(x(:,1), n); %FFT de uma das faixas de audio
f = (0:n-1)*(fa/n);
p = y.*conj(y)/n;
p = p./max(p);

%Plot da música no domínio frequência
figure(1)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlabel('Frequência (Hz)')

%Frequência dos filtros
%Passa-Baixas
fpb = 2*200/fa;

%Passa-Altas
fpa = 2*1000/fa;

%Passa-Banda
Fpp = 2*300/fa;
Fsp = 2*600/fa;

%Rejeita-Banda
Fpr = 2*900/fa;
Fsr = 2*700/fa;

%% B)