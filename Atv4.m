clc
clear all
close all

[x, fa] = audioread('Bagatelle-no.-25-__Für-Elise___-WoO-59.wav');

%% Escolha das frequecias dos filtros

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
fsb = 2*400/fa;

%Passa-Altas
fpa = 2*1700/fa;
fsa = 2*1900/fa;

%Passa-Banda   (fpp1*fpp2 = fsp1*fsp2)
fsp1 = 2*400/fa;
fpp1 = 2*600/fa;

fpp2 = 2*800/fa;
fsp2 = 2*1200/fa;

%Rejeita-Banda (fpr1*fpr2 = fsr1*fsr2)
fpr1 = 2*1300/fa;
fsr1 = 2*1500/fa;

fsr2 = 2*1700/fa;
fpr2 = 2*1961/fa;

%% Projeto dos filtros FIR

%Escolha da janela: hanning
%8pi/M
%Todos os filtro projetados tem como menor transisção de 0.0181*pi
%8pi/0.0181*pi = 441
%N escolhido: 450

%Passa-Baixas
hb = fir2(450,[0 fpb fsb 1], [1 1 0 0], hanning(451));
[hbf, wb] = freqz(hb);
%Passa-Altas
ha = fir2(450,[0 fpa fsa 1], [0 0 1 1], hanning(451));
[haf, wa] = freqz(ha);
%Passa-Banda
hp = fir2(450,[0 fsp1 fpp1 fpp2 fsp2 1], [0 0 1 1 0 0], hanning(451));
[hpf, wp] = freqz(hp);
%Rejeita-Banda
hr = fir2(450,[0 fpr1 fsr1 fsr2 fpr2 1], [1 1 0 0 1 1], hanning(451));
[hrf, wr] = freqz(hr);

figure(2)
hold on
plot(wb/pi,20*log10(abs(hbf)), 'b')
plot(wa/pi,20*log10(abs(haf)), 'r')
plot(wp/pi,20*log10(abs(hpf)), 'k')
plot(wr/pi,20*log10(abs(hrf)), 'g')
legend('Passa-Baixas', 'Passa-Altas', 'Passa-Banda', 'Rejeita-Banda')

%% Plot das respostas em frequencias dos filtros

y1 = filter(hb, 1, x(:,1));
y2 = filter(ha, 1, x(:,1));
y3 = filter(hp, 1, x(:,1));
y4 = filter(hr, 1, x(:,1));

figure(3)
hold on

%Passa-Baixas
y = fft(y1, n);
f = (0:n-1)*(fa/n);
p = y.*conj(y)/n;
p = p./max(p);

plot(f(1:floor(n/2)), p(1:floor(n/2)), 'b')

%Passa-Altas
y = fft(y2, n);
f = (0:n-1)*(fa/n);
p = y.*conj(y)/n;
p = p./max(p);

plot(f(1:floor(n/2)), p(1:floor(n/2)), 'r')

%Passa-Banda
y = fft(y3, n);
f = (0:n-1)*(fa/n);
p = y.*conj(y)/n;
p = p./max(p);

plot(f(1:floor(n/2)), p(1:floor(n/2)), 'k')

%Rejeita-Banda
y = fft(y4, n);
f = (0:n-1)*(fa/n);
p = y.*conj(y)/n;
p = p./max(p);

plot(f(1:floor(n/2)), p(1:floor(n/2)), 'g')

%% Sistema da fig. 1
G = [1 1 1 1];
yt = G(1)*y1 + G(2)*y2 + G(3)*y3 + G(4)*y4;

%sound(yt)

%% Gráfico de Atraso

figure(4)
subplot(2,2,1)
grpdelay(hb, 1)
title('Passa-Baixas')

subplot(2,2,2)
grpdelay(ha, 1)
title('Passa-Altas')

subplot(2,2,3)
grpdelay(hp, 1)
title('Passa-Banda')

subplot(2,2,4)
grpdelay(hr, 1)
title('Rejeita-Banda')

%% Pzmap dos filtros

figure(5)
subplot(2,2,1)
zplane(hb, 1)
title('Passa-Baixas')

subplot(2,2,2)
zplane(ha, 1)
title('Passa-Altas')

subplot(2,2,3)
zplane(hp, 1)
title('Passa-Banda')

subplot(2,2,4)
zplane(hr, 1)
title('Rejeita-Banda')