clc;
clear;
close all;

[x, fa] = audioread('AURORA - Running With The Wolves.wav');

%{
a) Escolher as frequências dos filtros com base 
no espectro de frequências do sinal de
áudio escolhido;
%}

n = pow2(nextpow2(length(x(:,1))));

y = fft(x(:,1) - mean(x(:,1)), n);
f = (0:n-1)*(fa/n);

p = y.*conj(y)/n;
p = p./max(p);

figure(1)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlim([0 fa/16])
xlabel('Frequência (Hz)')
ylabel('Magnitude normalizada')
title('Espectro de frequências do áudio')
grid on

%{
fa = 44100
famax = fa/2 = 22050

Portanto a frequência dos filtros será:
%}

%Passa-Baixas
fpb = 2*1000/fa;
fsb = 2*1300/fa;

%Passa-Altas
fpa = 2*10000/fa;
fsa = 2*12000/fa;

%Passa-Banda (bpfi * bpff = bpfis * bpffs)
bpfi = 2*1600/fa;
bpfis = 2*6000/fa;

bpff = 2*6250/fa;
bpffs = 2*8000/fa;

%Rejeita-Banda (brfi * brff = brfis * brffs)
brfi = 2*12000/fa;
brfis = 2*12500/fa;

brff = 2*14000/fa;
brffs = 2*14450/fa;

%{
b) Projetar um sistema somente com filtros 
do tipo FIR, e visualizar, em um único gráfico,
suas respostas em frequência;
%}

%Passa-Baixas
hb = fir2(100,[0 fpb fsb 1], [1 1 0 0], hann(101));
[hbf, wb] = freqz(hb);

%Passa-Altas
ha = fir2(100,[0 fpa fsa 1], [0 0 1 1], hann(101));
[haf, wa] = freqz(ha);

%Passa-Banda
hp = fir2(100,[0 bpfi bpfis bpff bpffs 1], [0 0 1 1 0 0], hann(101));
[hpf, wp] = freqz(hp);

%Rejeita-Banda
hr = fir2(100,[0 brfi brfis brff brffs 1], [1 1 0 0 1 1], hann(101));
[hrf, wr] = freqz(hr);

figure(2)
hold on

plot(wb/pi,20*log10(abs(hbf)), 'b')
plot(wa/pi,20*log10(abs(haf)), 'r')
plot(wp/pi,20*log10(abs(hpf)), 'g')
plot(wr/pi,20*log10(abs(hrf)), 'k')

xlabel('Frequência normalizada (\times\pi rad/amostra)')
ylabel('Magnitude (dB)')
title('Respostas em frequência dos filtros FIR')
legend('Passa-Baixas','Passa-Altas','Passa-Banda','Rejeita-Banda')


legTexts = findobj(lgd, 'Type', 'text');

legTexts(1).Color = 'k'; 
legTexts(2).Color = 'g';
legTexts(3).Color = 'b'; 
grid on


%{
c) Implementar cada sistema conforme diagrama da Figura 1;
%}



%{
d) Testar o funcionamento do sistema utilizando o arquivo de áudio
escolhido;
Testar saída de cada filtro individualmente alterando o valor dos ganhos
(G1, G2, G2 e G4), de "1" para "0" ou de "0" para "1".
%}
