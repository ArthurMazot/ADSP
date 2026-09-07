clc;
clear;
close all;

[x, fa] = audioread('AURORA - Running With The Wolves.wav');

%{
a) Escolher as frequencias dos filtros com base 
no espectro de frequencias do sinal de
Ã¡udio escolhido;
%}

n = pow2(nextpow2(length(x(:,1))));

y = fft(x(:,1) - mean(x(:,1)), n);
f = (0:n-1)*(fa/n);

p = y.*conj(y)/n;
p = p./max(p);

figure(1)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlim([0 fa/16])
xlabel('Frequencia (Hz)')
ylabel('Magnitude normalizada')
title('Espectro de frequencias do audio')
grid on

%{
fa = 44100
famax = fa/2 = 22050

Portanto a frequencia dos filtros sera¡:
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
do tipo FIR, e visualizar, em um unico grafico,
suas respostas em frequencia;
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

xlabel('Frequencia normalizada (\times\pi rad/amostra)')
ylabel('Magnitude (dB)')
title('Respostas em frequencia dos filtros FIR')
legend('Passa-Baixas','Passa-Altas','Passa-Banda','Rejeita-Banda')

grid on


%{
c) Implementar cada sistema conforme diagrama da Figura 1;
%}

%Filtragem do sinal de áudio em cada filtro
y1 = filter(hb, 1, x(:,1)); %Passa-Baixas
y2 = filter(ha, 1, x(:,1)); %Passa-Altas
y3 = filter(hp, 1, x(:,1)); %Passa-Banda
y4 = filter(hr, 1, x(:,1)); %Rejeita-Banda

figure(3)
hold on

Y = [y1 y2 y3 y4];
cores = ['b' 'r' 'g' 'k'];

for i = 1:4
    y = fft(Y(:,i), n);
    p = y.*conj(y)/n;
    p = p./max(p);

    plot(f(1:floor(n/2)), p(1:floor(n/2)), cores(i))
end

xlabel('Frequência (Hz)')
ylabel('Magnitude normalizada')
title('Espectro das saídas dos filtros FIR')
legend('Passa-Baixas','Passa-Altas','Passa-Banda','Rejeita-Banda')
xlim([0 18000])
grid on

%{
d) Testar o funcionamento do sistema utilizando o arquivo de Ã¡udio
escolhido;
Testar saÃ­da de cada filtro individualmente alterando o valor dos ganhos
(G1, G2, G2 e G4), de "1" para "0" ou de "0" para "1".
%}

G = [1 1 1 1]; %Ganhos dos filtros
yt = G(1)*y1 + G(2)*y2 + G(3)*y3 + G(4)*y4; %Soma das saídas dos filtros
%sound(yt, fa) %Reproduz o áudio filtrado

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
grid on


% Diagrama de Polos e Zeros

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
grid on

