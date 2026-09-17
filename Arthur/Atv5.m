clc
clear all
close all

format long g

Amax = 0.5;
Amin = 40;
Fs = 22050;

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
[NUM,DEN] = bilinear(bt,at,Fs);

% Determina H(z)
hpb = tf(NUM, DEN, -1, 'variable','z^-1');

%Gráfico de módulo e fase
figure(1)
freqz(NUM,DEN)

%Atraso de Grupo
figure(2)
subplot(1,2,1)
grpdelay(NUM,DEN)

%Polos e zeros
subplot(1,2,2)
zplane(NUM,DEN)

%Plotar Resposta em Frequencia da H(z) obtida pela Transformação Bilinear
H = freqz(NUM,DEN,w); 
 
%Verificar Requisitos 
var1 = ceil(wp/var+1); 
var2 = ceil(wr/var+1);  

mod_0 = 20*log10(abs(H(1)));
mod_wp = 20*log10(abs(H(var1))); 
mod_wr = 20*log10(abs(H(var2)));

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
[NUM,DEN] = bilinear(bt1,at1,Fs);

% Determina H(z)
hpa = tf(NUM, DEN, -1, 'variable','z^-1');

%Plotar Resposta em Frequencia da H(z) obtida pela Transformação Bilinear
H = freqz(NUM,DEN,w);

%Plotar módulo e fase
figure(3)
freqz(NUM,DEN)

%Plotar atraso de grupo
figure(4)
subplot(1,2,1)
grpdelay(NUM,DEN)

%polos e zeros
subplot(1,2,2)
zplane(NUM,DEN)

%Verificar Requisitos
var1 = ceil(wp/var+1);
var2 = ceil(wr/var+1);

mod_0 = 20*log10(abs(H(1)));
mod_wp = 20*log10(abs(H(var1)));
mod_wr = 20*log10(abs(H(var2)));

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
[NUM,DEN] = bilinear(bt2,at2,Fs);

%Plotar Resposta em Frequencia
H = freqz(NUM,DEN,w);

%Plotar módulo e fase
figure(5)
freqz(NUM,DEN)

%Plotar atraso de grupo
figure(6)
subplot(1,2,1)
grpdelay(NUM,DEN)

%polos e zeros
subplot(1,2,2)
zplane(NUM,DEN)

%Verificar Requisitos 

var1 = ceil(wp(1)/var+1);
var2 = ceil(wp(2)/var+1);
var3 = ceil(wr(1)/var+1);  
var4 = ceil(wr(2)/var+1);  

mod_0 = 20*log10(abs(H(1)));
mod_wp1 = 20*log10(abs(H(var1))); 
mod_wp2 = 20*log10(abs(H(var2)));
mod_wr1 = 20*log10(abs(H(var3))); 
mod_wr2 = 20*log10(abs(H(var4)));

fprintf('Validação do Passa-Banda\nmod_0 = %f\nmod_wp1 = %f\nmod_wp2 = %f\nmod_wr1 = %f\nmod_wr2 = %f\n\n', mod_0, mod_wp1, mod_wp2, mod_wr1, mod_wr2)
%% Rejeita-Banda

%Frequência analógica em rad/s
wp = [2*pi*200 2*pi*6000];    % [wp1 wp2] ou [w1 w2]
wr = [2*pi*400 2*pi*1500];     % [ws1 ws2] ou [w3 w4]

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
[NUM,DEN] = bilinear(bt3,at3,Fs);

%Plotar Resposta em Frequencia
H = freqz(NUM,DEN,w);

%Plotar módulo e fase
figure(7)
freqz(NUM,DEN)

%Plotar atraso de grupo
figure(8)
subplot(1,2,1)
grpdelay(NUM,DEN)

%polos e zeros
subplot(1,2,2)
zplane(NUM,DEN)

%Verificar Requisitos 

var1 = ceil(wp(1)/var+1);
var2 = ceil(wp(2)/var+1);
var3 = ceil(wr(1)/var+1);  
var4 = ceil(wr(2)/var+1);  

mod_0 = 20*log10(abs(H(1)));
mod_wp1 = 20*log10(abs(H(var1)));  
mod_wp2 = 20*log10(abs(H(var2)));
mod_wr1 = 20*log10(abs(H(var3))); 
mod_wr2 = 20*log10(abs(H(var4)));

fprintf('Validação do Rejeita-Banda\nmod_0 = %f\nmod_wp1 = %f\nmod_wp2 = %f\nmod_wr1 = %f\nmod_wr2 = %f\n\n', mod_0, mod_wp1, mod_wp2, mod_wr1, mod_wr2)
