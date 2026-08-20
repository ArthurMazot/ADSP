clc
clear all
close all

%% B)
[x, fs, bits]  = wavread('Bagatelle-no.-25-__Für-Elise___-WoO-59.wav'); %Le o arquivo .wav

bCall = x(:,1);
tb = (0:1/fs:(length(bCall)-1)/fs);


figure(1)
plot(tb, bCall)
xlim([0 tb(end)])
xlabel('Tempo (segundos)')
ylabel('Amplitude')
title('{\bf Audio}')

%sound(bCall, fs);

%% C)

m = length(bCall); %
n = pow2(nextpow2(m)); %Corrige para a próxima potencia de 2

y = fft(bCall, n);
f = (0:n-1)*(fs/n);
p = y.*conj(y)/n;
p = p./max(p);

figure(2)
subplot(2,1,1)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlabel('Frequência (Hz)')

subplot(2,1,2)
plot(f(1:floor(n/2)), angle(y(1:floor(n/2))))

%% D)

aux = bCall + 0.02*cos(2*pi*4000*tb)';
figure(4)
plot(aux)

m = length(aux); %
n = pow2(nextpow2(m)); %Corrige para a próxima potencia de 2

%% E)

y = fft(aux, n);
f = (0:n-1)*(fs/n);
p = abs(y)/n;
p = p./max(p);

figure(3)
subplot(2,1,1)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlabel('Frequência (Hz)')

subplot(2,1,2)
plot(f(1:floor(n/2)), angle(y(1:floor(n/2))))

%% Parte 2)

