clc
clear all
close all

Amax = 0.5;
Amin = 40;

E = sqrt(10^(0.1*Amax)-1);
w = 0:pi/100000:pi;

[x, fa] = audioread('Bagatelle-no.-25-__Für-Elise___-WoO-59.wav');

%% Projeto dos filros
%Passa-baixas

Wp = 2*pi*200/fa;
Ws = 2*pi*400/fa;

Wpb = 2*fa*tan(Wp/2);
Wsb = 2*fa*tan(Ws/2);

[n, wo] = cheb1ord(Wpb, Wsb, Amax, Amin, 's');

[z,p,k]=cheb1ap(n, Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
[b,a]=lp2lp(b,a,wo);

%Transformaçao Bilinear
[NUM,DEN] = bilinear(b,a,fa);
H = freqz(NUM,DEN,w);

%Vericação
var = (pi/100000);
var1 = ceil(Wp/var+1);
var2 = ceil(Ws/var+1);
mod_0 = 20*log10(abs(H(1)));
mod_wp = 20*log10(abs(H(var1)));
mod_wr = 20*log10(abs(H(var2)));

fprintf('Validação do Passa-Baixas\nmod_0 = %f\nmod_wp = %f\nmod_wr = %f\n\n', mod_0, mod_wp, mod_wr)

%Passa-Altas
Ws = 1700*pi*2/fa;
Wp = 1900*pi*2/fa;

Wsa = 2*fa*tan(Ws/2);
Wpa = 2*fa*tan(Wp/2);

% Cálculo da Ordem e da frequência de 3 dB
[n, wo] = cheb1ord(Wpa,Wsa,Amax,Amin,'s');

% Determina numerador e denominador da H(s) do filtro analógico
[z,p,k]=cheb1ap(n,Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
[b,a]=lp2hp(b,a,wo);

%Transformaçao Bilinear
[NUM,DEN] = bilinear(b,a,fa);
H = freqz(NUM,DEN,w);

%Vericação
var = (pi/100000);
var1 = ceil(Wp/var+1);
var2 = ceil(Ws/var+1);
mod_0 = 20*log10(abs(H(1)));
mod_wp = 20*log10(abs(H(var1)));
mod_wr = 20*log10(abs(H(var2)));

fprintf('Validação do Passa-Altas\nmod_0 = %f\nmod_wp = %f\nmod_wr = %f\n\n', mod_0, mod_wp, mod_wr)

%Passa-Banda   (fpp1*fpp2 = fsp1*fsp2)
Wp = [600*2*pi/fa 800*2*pi/fa];
Ws = [400*2*pi/fa 1200*2*pi/fa];
B = Wp(2) - Wp(1);

Wsp = 2*fa*tan(Wp/2);
Wpp = 2*fa*tan(Ws/2);

[n,wo]=buttord(Wpp,Wsp,Amax,Amin,'s');
E1 = E^(1/n);
B1 = B/E1;

[z,p,k]=buttap(n);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
[b,a]=lp2bp(b,a,wo,B1);

%Transformaçao Bilinear
[NUM,DEN] = bilinear(b,a,fa);

%Vericação
w = 0:pi/512:pi;
H = freqz(NUM,DEN,w);
figure(2)
plot(w,abs(H))
grid on

fprintf('Validação do Passa-Banda\nmod_0 = %f\nmod_wp = %f\nmod_wr = %f\n\n', mod_0, mod_wp, mod_wr)

%Rejeita-Banda (fpr1*fpr2 = fsr1*fsr2)

fprintf('Validação do Rejeita-Banda\nmod_0 = %f\nmod_wp = %f\nmod_wr = %f\n\n', mod_0, mod_wp, mod_wr)

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