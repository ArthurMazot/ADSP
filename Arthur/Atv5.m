clc
clear all
close all

Amax = 0.5;
Amin = 40;

[x, fa] = audioread('Bagatelle-no.-25-__Für-Elise___-WoO-59.wav');

%% Projeto dos filros
%Passa-baixas

Wpb = 2*fa*tan(200/(fa*2));
Wsb = 2*fa*tan(400/(fa*2));

[n, wo] = cheb1ord(Wpb, Wsb, Amax, Amin, 's');

[z,p,k]=cheb1ap(n, Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
[bt,at]=lp2lp(b,a,wo);

%Transformaçao Bilinear
[NUM,DEN] = bilinear(bt,at,fa);

% Determina H(z)
Hzb = tf(NUM, DEN, -1, 'variable','z^-1');

w = 0:pi/100000:pi;
H = freqz(NUM,DEN,w);

%Vericação
fprintf('Validação do Passa-Baixas\n')
var = (pi/100000);
var1 = ceil((200/fa)/var+1);
var2 = ceil((400/fa)/var+1);
mod_0 = 20*log10(abs(H(1)))
mod_wp = 20*log10(abs(H(var1)))
mod_wr = 20*log10(abs(H(var2)))

%Passa-Altas
Wpa = 2*fa*tan(1700/(fa*2));
Wsa = 2*fa*tan(1900/(fa*2));

%Passa-Banda   (fpp1*fpp2 = fsp1*fsp2)
Wsp1 = 2*fa*tan(400/(fa*2));
Wpp1 = 2*fa*tan(600/(fa*2));

Wpp2 = 2*fa*tan(800/(fa*2));
Wsp2 = 2*fa*tan(1200/(fa*2));

%Rejeita-Banda (fpr1*fpr2 = fsr1*fsr2)
Wpr1 = 2*fa*tan(1300/(fa*2));
Wsr1 = 2*fa*tan(1500/(fa*2));

Wsr2 = 2*fa*tan(1700/(fa*2));
Wpr2 = 2*fa*tan(1961/(fa*2));


%% Sinal x[n]
n = pow2(nextpow2(length(x(:,1)))); %Corrige para a próxima potencia de 2

y = fft(x(:,1), n); %FFT de uma das faixas de audio
f = (0:n-1)*(fa/n);
p = y.*conj(y)/n;
p = p./max(p);

%Plot da música no domínio frequência
figure(1)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlabel('Frequência (Hz)')
