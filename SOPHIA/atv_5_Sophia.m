clc
clear all
close all

Amax = 0.5;
Amin = 40;

E = sqrt(10^(0.1*Amax)-1);
w = 0:pi/100000:pi;

[x, fa] = audioread('AURORA - Running With The Wolves.wav');

%{
a) Escolher as frequências dos filtros com base no espectro
de frequências do sinal de áudio da Prática 4.

Frequência de amostragem:
fa = 44100 Hz

Frequência máxima:
fa/2 = 22050 Hz
%}

n = pow2(nextpow2(length(x(:,1))));

y = fft(x(:,1), n);
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
Frequências escolhidas com base na Prática 4.
%}

% Passa-Baixas
fpb = 2*1000/fa;
fsb = 2*1300/fa;

% Passa-Altas
fpa = 2*10000/fa;
fsa = 2*12000/fa;

% Passa-Banda
bpfi = 2*1600/fa;
bpfis = 2*6000/fa;

bpff = 2*6250/fa;
bpffs = 2*8000/fa;

% Rejeita-Banda
brfi = 2*12000/fa;
brfis = 2*12500/fa;

brff = 2*14000/fa;
brffs = 2*14450/fa;

%{
b) Projetar filtros IIR, Butterworth ou Chebyshev I, para serem
utilizados no sistema de filtragem da Prática 4.

%}

% Passa-Baixas
Wp = 2*pi*1000/fa;
Ws = 2*pi*1300/fa;

Wpb = 2*fa*tan(Wp/2);
Wsb = 2*fa*tan(Ws/2);

% Cálculo da ordem do filtro
[n, wo] = cheb1ord(Wpb, Wsb, Amax, Amin, 's');

% Determinação do filtro normalizado
[z,p,k] = cheb1ap(n, Amax);
b = poly(z)*k;
a = poly(p);

% Transformação do filtro
[b,a] = lp2lp(b,a,wo);

% Transformação Bilinear
[NUM,DEN] = bilinear(b,a,fa);

% Determina H(z)
H = freqz(NUM,DEN,w);

% Verificação
var = pi/100000;
var1 = ceil(Wp/var+1);
var2 = ceil(Ws/var+1);

mod_0 = 20*log10(abs(H(1)));
mod_wp = 20*log10(abs(H(var1)));
mod_wr = 20*log10(abs(H(var2)));

fprintf('Validação do Passa-Baixas\n')
fprintf('Ordem = %d\n', n)
fprintf('mod_0 = %f dB\n', mod_0)
fprintf('mod_wp = %f dB\n', mod_wp)
fprintf('mod_wr = %f dB\n\n', mod_wr)

% Gráfico da resposta em frequência
figure(2)
freqz(NUM,DEN)