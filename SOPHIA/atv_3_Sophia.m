%% Atividade Prática
%{
a) Analisar o espectro de um arquivo de áudio .wav, 
da escolha do aluno(a);
%}

clc;
clear;
close all;

[x, fs] = audioread('AURORA - Running With The Wolves.wav');

size(x); % Se numberx2 -> Significa 2 canais de áudio
%sound(bCall, fs); %Play Music

bCall = x(:,1);

%{
b) Plotar sinal no domínio do tempo;
%}

tb = (0:1/fs:(length(bCall)-1)/fs);

figure(1);
plot(tb,bCall);
xlim([0 tb(end)]);
xlabel('Tempo (s)');
ylabel('Amplitude');
title('Áudio - Domínio do Tempo');

%{
c) Traçar as curvas do espectro (modulo/abs e fase/angle) com escala de
frequências em Hertz;
%}

m = length(bCall);            
n = pow2(nextpow2(m)); % Tamanho da FFT

y = fft(bCall,n);
freqH = (0:n-1)*(fs/n); 

figure(2);

subplot(2,1,1);
plot(freqH, abs(y));
xlabel('Frequência (Hz)');
ylabel('Magnitude');
title('Espectro de Magnitude - Áudio Original');

subplot(2,1,2);
plot(freqH, angle(y));
xlabel('Frequência (Hz)');
ylabel('Fase (rad)');
title('Espectro de Fase - Áudio Original');

%{
d) Adicionar uma interferência de 4kHz e 
visualizar novamente o espectro;
%}

interfCos = 0.02*cos(2*pi*4000*tb)';
bCallInterf = bCall + interfCos;

yInterf = fft(bCallInterf, n);

figure(3);

subplot(2,1,1);
plot(freqH, abs(yInterf));
xlabel('Frequência (Hz)');
ylabel('Magnitude');
title('Espectro de Magnitude - Áudio com Interferência de 4 kHz');

subplot(2,1,2);
plot(freqH, angle(yInterf));
xlabel('Frequência (Hz)');
ylabel('Fase (rad)');
title('Espectro de Fase - Áudio com Interferência de 4 kHz');

%{
e) Apresentar o espectro na faixa de 0 até fs/2 e a magnitude (linear) deverá
ser normalizada para que seu valor máximo seja unitário. 
%}

p = yInterf.*conj(yInterf)/n;
p = p./max(p);

figure(4)
subplot(2,1,1)
plot(freqH(1:floor(n/2)), p(1:floor(n/2)))
xlabel('Frequência (Hz)')
ylabel('Potência Normalizada')
title('Espectro Normalizado - Áudio com Interferência de 4 kHz');

subplot(2,1,2)
plot(freqH(1:floor(n/2)), angle(yInterf(1:floor(n/2))))
xlabel('Frequência (Hz)')
ylabel('Fase (rad)')
title('Fase - Áudio com Interferência de 4 kHz');
