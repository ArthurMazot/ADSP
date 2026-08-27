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
fpb = 2*500/fa;
fsb = 2*1300/fa;

%Passa-Altas
fpa = 2*9000/fa;
fsa = 2*10000/fa;

%Passa-Banda   (fpp1*fpps2 = fsp1*fsp2)
fsp1 = 2*1600/fa;
fpp1 = 2*2500/fa;

fpp2 = 2*4000/fa;
fsp2 = 2*6250/fa;

%Rejeita-Banda (fpr1*fprs2 = fsr1*fsr2)
fpr1 = 2*6000/fa;
fsr1 = 2*6500/fa;

fsr2 = 2*8000/fa;
fpr2 = 2*8450/fa;

%% B)

%Passa-Baixas
[hb, wb] = freqz(fir2(50,[0 fpb fsb 1], [1 1 0 0], hanning(51)));
%Passa-Altas
[ha, wa] = freqz(fir2(50,[0 fpa fsa 1], [0 0 1 1], hanning(51)));
%Passa-Banda
[hp, wp] = freqz(fir2(50,[0 fsp1 fpp1 fpp2 fsp2 1], [0 0 1 1 0 0], hanning(51)));
%Rejeita-Banda
[hr, wr] = freqz(fir2(50,[0 fpr1 fsr1 fsr2 fpr2 1], [1 1 0 0 1 1], hanning(51)));

figure(2)
hold on
plot(wb/pi,20*log10(abs(hb)), 'b')
plot(wa/pi,20*log10(abs(ha)), 'r')
plot(wp/pi,20*log10(abs(hp)), 'k')
plot(wr/pi,20*log10(abs(hr)), 'g')
legend('Passa-Baixas', 'Passa-Altas', 'Passa-Banda', 'Rejeita-Banda')

%% C)

y1 = filter(hb, 1, x(:,1));
y2 = filter(ha, 1, x(:,1));
y3 = filter(hp, 1, x(:,1));
y4 = filter(hr, 1, x(:,1));

yt = y1 + y2 + y3 + y4;
plot(yt)

%% D)
G = [0 0 0 0];
yt = G(1)*y1 + G(2)*y2 + G(3)*y3 + G(4)*y4;
