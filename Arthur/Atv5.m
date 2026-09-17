clc
clear all
close all

format long g

[x, Fs] = audioread('Bagatelle-no.-25-__Für-Elise___-WoO-59.wav');


Amax = 0.5;
Amin = 40;

w = 0:pi/10000:pi;
var = pi/10000;
%% Passa-Baixas

wp = 2*pi*200;
wr = 2*pi*400;

Wp1 = wp;
Wr1 = wr;

wp = Wp1/Fs;
wr = Wr1/Fs;

%Pré-distorção das frequências
Wap = 2*Fs*tan(wp/2);
War = 2*Fs*tan(wr/2);

%Calculo da ordem do Filtro
[n,~]=cheb1ord(Wap,War,Amax,Amin,'s');
wo = Wap;

%Determinaçao do filtro normalizado
[z,p,k]=cheb1ap(n,Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
[bt,at]=lp2lp(b,a,wo);

%Transformaçao Bilinear
[NUM1,DEN1] = bilinear(bt,at,Fs);

figure(3)
hold on
hb = freqz(NUM1,DEN1,w);
plot(w/pi, 20*log10(abs(hb)), 'b')

%Atraso de Grupo
figure(1)
subplot(2,2,1)
grpdelay(NUM1,DEN1)
title('Passa-Baixa')
xlim([0 0.5])

%Polos e zeros
figure(2)
subplot(2,2,1)
zplane(NUM1,DEN1)
title('Passa-Baixa')

%Verificar Requisitos 
var1 = ceil(wp/var+1); 
var2 = ceil(wr/var+1);  

mod_0 = 20*log10(abs(hb(1)));
mod_wp = 20*log10(abs(hb(var1))); 
mod_wr = 20*log10(abs(hb(var2)));

fprintf('Validação do Passa-Baixas\nmod_0 = %f\nmod_wp = %f\nmod_wr = %f\n\n', mod_0, mod_wp, mod_wr)
%% Passa-Altas

%Frequências analógicas de passagem e rejeição em rad/s
wr = 1700*pi*2;
wp = 1900*pi*2;

Wp1 = wp;
Wr1 = wr;

wp = Wp1/Fs;
wr = Wr1/Fs;

%Pré-distorção das frequências
Wap = 2*Fs*tan(wp/2);
War = 2*Fs*tan(wr/2);

%Calculo da ordem do Filtro
[n,~]=cheb1ord(Wap,War,Amax,Amin,'s');
wo = Wap;

%Determinaçao do filtro normalizado
[z,p,k]=cheb1ap(n,Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
[bt1,at1]=lp2hp(b,a,wo);

%Transformaçao Bilinear
[NUM2,DEN2] = bilinear(bt1,at1,Fs);

%Plotar Resposta em Frequencia da H(z) obtida pela Transformação Bilinear
figure(3)
hold on
ha = freqz(NUM2,DEN2,w);
plot(w/pi, 20*log10(abs(ha)), 'r')

%Plotar atraso de grupo
figure(1)
subplot(2,2,2)
grpdelay(NUM2,DEN2)
title('Passa-Alta')
xlim([0 0.5])

%polos e zeros
figure(2)
subplot(2,2,2)
zplane(NUM2,DEN2)
title('Passa-Alta')

%Verificar Requisitos
var1 = ceil(wp/var+1);
var2 = ceil(wr/var+1);

mod_0 = 20*log10(abs(ha(1)));
mod_wp = 20*log10(abs(ha(var1)));
mod_wr = 20*log10(abs(ha(var2)));

fprintf('Validação do Passa-Altas\nmod_0 = %f\nmod_wp = %f\nmod_wr = %f\n\n', mod_0, mod_wp, mod_wr)

%% Passa-Banda

%Frequência analógica em rad/s
wp = [600*2*pi 800*2*pi];
wr = [400*2*pi 1200*2*pi];

%Frequências digitais
Wp1 = wp;
Wr1 = wr;

wp = Wp1/Fs;
wr = Wr1/Fs;

%Pré-distorção das frequências
Wap = 2*Fs*tan(wp/2);
War = 2*Fs*tan(wr/2);

%Calculo da ordem do Filtro
[n,~]=cheb1ord(Wap,War,Amax,Amin,'s');

%Determinaçao do filtro normalizado
[z,p,k]=cheb1ap(n,Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
B1 = Wap(2)-Wap(1);
Wao = sqrt(Wap(1)*Wap(2));

[bt2,at2]=lp2bp(b,a,Wao,B1);

%Transformaçao Bilinear
[NUM3,DEN3] = bilinear(bt2,at2,Fs);

%Plotar Resposta em Frequencia
figure(3)
hold on
hp = freqz(NUM3,DEN3,w);
plot(w/pi, 20*log10(abs(hp)), 'k')

%Plotar atraso de grupo
figure(1)
subplot(2,2,3)
grpdelay(NUM3,DEN3)
title('Passa-Banda')
xlim([0 0.5])

%polos e zeros
figure(2)
subplot(2,2,3)
zplane(NUM3,DEN3)
title('Passa-Banda')

%Verificar Requisitos 

var1 = ceil(wp(1)/var+1);
var2 = ceil(wp(2)/var+1);
var3 = ceil(wr(1)/var+1);  
var4 = ceil(wr(2)/var+1);  

mod_0 = 20*log10(abs(hp(1)));
mod_wp1 = 20*log10(abs(hp(var1))); 
mod_wp2 = 20*log10(abs(hp(var2)));
mod_wr1 = 20*log10(abs(hp(var3))); 
mod_wr2 = 20*log10(abs(hp(var4)));

fprintf('Validação do Passa-Banda\nmod_0 = %f\nmod_wp1 = %f\nmod_wp2 = %f\nmod_wr1 = %f\nmod_wr2 = %f\n\n', mod_0, mod_wp1, mod_wp2, mod_wr1, mod_wr2)
%% Rejeita-Banda

%Frequência analógica em rad/s
wp = [2*pi*1300 2*pi*1961];
wr = [2*pi*1500 2*pi*1700];

%Frequências digitais
Wp1 = wp;
Wr1 = wr;

wp = Wp1/Fs;
wr = Wr1/Fs;

%Pré-distorção das frequências
Wap = 2*Fs*tan(wp/2);
War = 2*Fs*tan(wr/2);

%Calculo da ordem do Filtro
[n,wn]=cheb1ord(Wap,War,Amax,Amin,'s');

%Determinaçao do filtro normalizado
[z,p,k]=cheb1ap(n,Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
B1 = Wap(2)-Wap(1);
Wao = sqrt(Wap(1)*Wap(2));

[bt3,at3]=lp2bs(b,a,Wao,B1);

%Transformaçao Bilinear
[NUM4,DEN4] = bilinear(bt3,at3,Fs);

%Plotar Resposta em Frequencia
figure(3)
hold on
hr = freqz(NUM4,DEN4,w);
plot(w/pi, 20*log10(abs(hr)),'g')

%Plotar atraso de grupo
figure(1)
subplot(2,2,4)
grpdelay(NUM4,DEN4)
title('Rejeita-Banda')
xlim([0 0.5])

%polos e zeros
figure(2)
subplot(2,2,4)
zplane(NUM4,DEN4)
title('Resjeira-Banda')

%Verificar Requisitos 

var1 = ceil(wp(1)/var+1);
var2 = ceil(wp(2)/var+1);
var3 = ceil(wr(1)/var+1);  
var4 = ceil(wr(2)/var+1);  

mod_0 = 20*log10(abs(hr(1)));
mod_wp1 = 20*log10(abs(hr(var1)));  
mod_wp2 = 20*log10(abs(hr(var2)));
mod_wr1 = 20*log10(abs(hr(var3))); 
mod_wr2 = 20*log10(abs(hr(var4)));

fprintf('Validação do Rejeita-Banda\nmod_0 = %f\nmod_wp1 = %f\nmod_wp2 = %f\nmod_wr1 = %f\nmod_wr2 = %f\n\n', mod_0, mod_wp1, mod_wp2, mod_wr1, mod_wr2)
%% Correção dos plots

figure(3)
hold on
legend('Passa-Baixa', 'Passa-Alta', 'Passa-Banda', 'Rejeita-Banda')
xlim([0 0.4])

%% Plot de x(t) em frequencia
n = pow2(nextpow2(length(x(:,1)))); %Corrige para a próxima potencia de 2

y = fft(x(:,1), n); %FFT de uma das faixas de audio
f = (0:n-1)*(Fs/n);
p = y.*conj(y)/n;
p = p./max(p);

%Plot da música no domínio frequência
figure(4)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlabel('Frequência (Hz)')
xlim([0 4410])

%% Plot das respostas em frequencias dos filtros


y1 = filter(NUM1, DEN1, x(:,1));
y2 = filter(NUM2, DEN2, x(:,1));
y3 = filter(NUM3, DEN3, x(:,1));
y4 = filter(NUM4, DEN4, x(:,1));

figure(5)
hold on

%Passa-Baixas
y = fft(y1, n);
f = (0:n-1)*(Fs/n);
p = y.*conj(y)/n;
p = p./max(p);

plot(f(1:floor(n/2)), p(1:floor(n/2)), 'b')

%Passa-Altas
y = fft(y2, n);
f = (0:n-1)*(Fs/n);
p = y.*conj(y)/n;
p = p./max(p);

plot(f(1:floor(n/2)), p(1:floor(n/2)), 'r')

%Passa-Banda
y = fft(y3, n);
f = (0:n-1)*(Fs/n);
p = y.*conj(y)/n;
p = p./max(p);

plot(f(1:floor(n/2)), p(1:floor(n/2)), 'k')

%Rejeita-Banda
y = fft(y4, n);
f = (0:n-1)*(Fs/n);
p = y.*conj(y)/n;
p = p./max(p);

plot(f(1:floor(n/2)), p(1:floor(n/2)), 'g')
xlim([0 4410])

%% Sistema
G = [1 1 1 1];
yt = G(1)*y1 + G(2)*y2 + G(3)*y3 + G(4)*y4;
