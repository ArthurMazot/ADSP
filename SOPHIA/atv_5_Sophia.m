clc;
clear;
close all;

format long g

[x, fa] = audioread('AURORA - Running With The Wolves.wav');

%{
a) Escolher as frequências dos filtros com base no espectro de frequências do sinal de
áudio da prática 4;
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

% Ver frequencias menores
figure(2)
plot(f(1:floor(n/2)), 10*log10(p(1:floor(n/2))))
xlim([0 16000])
xlabel('Frequência (Hz)')
ylabel('Magnitude (dB)')
title('Espectro de frequências do áudio')
grid on

%sound(x,fa)

%{
    Frequências escolhida dos filtros
%} 

%Passa-Baixas
fpb = 1000;  %Freq. passagem
fsb = 1300;  %Freq. rejeição

%Passa-Altas
fsa = 10000; %Freq. rejeição 
fpa = 12000; %Freq. passagem

%Passa-Banda
bpfis  = 1600; %Rej Inf
bpfi = 6000;   %Pass Inf

bpff  = 6250;  %Pass Sup
bpffs = 8000;  %Rej Sup

%Rejeita-Banda
brfi  = 12000; %Pass Inf
brfis = 12500; %Rej Inf

brff  = 14000; %Rej Sup
brffs = 14450; %Pass Sup

%{
b) Testar o funcionamento de cada filtro com o arquivo de áudio da prática 4;
%}

%Especificações dos filtros IIR
Amax = 0.5; %Atenuação máx banda de passagem (dB)
Amin = 40;  %Atenuação mín banda de rejeição (dB)

%Passa-Baixas

%Frequências digitais em rad/amostra
%{
    Frequencias iniciais em Hz conversão necessária para rad/amostra
%}
wp = 2*pi*fpb/fa;
wr = 2*pi*fsb/fa;

%Pré-distorção das frequências
Wap = 2*fa*tan(wp/2);
War = 2*fa*tan(wr/2);

%Calculo da ordem do filtro
[n,wn] = cheb1ord(Wap,War,Amax,Amin,'s');

%Determinação do filtro normalizado
[z,p,k] = cheb1ap(n,Amax);
b = poly(z)*k;
a = poly(p);

%Transformação do filtro
[bt,at] = lp2lp(b,a,Wap);

%Transformação Bilinear
[NUMb,DENb] = bilinear(bt,at,fa);

% Determina H(z)
hb = tf(NUMb, DENb, -1, 'variable','z^-1');

%Gráfico de módulo e fase
figure(3)
freqz(NUMb,DENb);
title('Gráfico de módulo e fase - Passas-baixa')

%Atraso de Grupo
figure(4)
grpdelay(NUMb,DENb)
title('Atraso de Grupo - Passas-baixa')

%Polos e zeros
figure(5)
zplane(NUMb,DENb)
title('Polos e zeros - Passas-baixa')

%Plotar Resposta em Frequencia da H(z) obtida pela Transformação Bilinear
w = 0:pi/10000:pi; % Poucos pontos 512, necessário aumentar
H = freqz(NUMb,DENb,w);

%Verificar Requisitos
var = (pi/10000);
var1 = ceil(wp/var+1);
var2 = ceil(wr/var+1);

fprintf('\n--- PASSA-BAIXAS ---\n')
%w = 0
mod_0 = 20*log10(abs(H(1)))

%w = wp
mod_wp = 20*log10(abs(H(var1)))

%w = wr
mod_wr = 20*log10(abs(H(var2)))


% 2 - Filtro Passa-Altas
%Frequências digitais em rad/amostra
wp = 2*pi*fpa/fa;
wr = 2*pi*fsa/fa;

%Pré-distorção das frequências
Wap = 2*fa*tan(wp/2);
War = 2*fa*tan(wr/2);

%Calculo da ordem do Filtro
[n,wn] = cheb1ord(Wap,War,Amax,Amin,'s');
wo = Wap;

%Determinaçao do filtro normalizado
[z,p,k] = cheb1ap(n,Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
[bt1,at1] = lp2hp(b,a,wo);

%Transformaçao Bilinear
[NUMa,DENa] = bilinear(bt1,at1,fa);

% Determina H(z)
ha = tf(NUMa,DENa,-1,'variable','z^-1');

%Gráfico de módulo e fase
figure
freqz(NUMa,DENa)
title('Gráfico de módulo e fase - Passas-altas')

%Atraso de Grupo
figure
grpdelay(NUMa,DENa)
title('Atraso de Grupo - Passas-altas')

%Polos e zeros
figure
zplane(NUMa,DENa)
title('Polos e zeros - Passas-altas')

%Plotar Resposta em Frequencia da H(z)
w = 0:pi/10000:pi;
H = freqz(NUMa,DENa,w);

%Verificar Requisitos
var = (pi/10000);
var1 = ceil(wp/var+1);
var2 = ceil(wr/var+1);

fprintf('\n--- PASSA-ALTAS ---\n')

%w = 0
mod_0 = 20*log10(abs(H(1)))

%w = wp
mod_wp = 20*log10(abs(H(var1)))

%w = wr
mod_wr = 20*log10(abs(H(var2)))


% 3 - Filtro passa-banda
%Frequências digitais
wp = 2*pi*[bpfi bpff]/fa;
wr = 2*pi*[bpfis bpffs]/fa;

%Pré-distorção das frequências
Wap = 2*fa*tan(wp/2);
War = 2*fa*tan(wr/2);

%Calculo da ordem do Filtro
[n,wn]=cheb1ord(Wap,War,Amax,Amin,'s');

%Determinaçao do filtro normalizado
[z,p,k]=cheb1ap(n,Amax);
b = poly(z)*k;
a = poly(p);

%Transformaçao do filtro
B1 = Wap(2)-Wap(1);
Wao = sqrt(Wap(1)*Wap(2));

[bt2,at2]=lp2bp(b,a,Wao,B1);

%Transformaçao Bilinear
[NUMp,DENp] = bilinear(bt2,at2,fa);

%Plotar Resposta em Frequencia
w = 0:pi/10000:pi;
H = freqz(NUMp,DENp,w);

% Determina H(z)
hp = tf(NUMp, DENp, -1, 'variable','z^-1');

%Plotar módulo e fase
figure
freqz(NUMp,DENp)
title('Gráfico de módulo e fase - Passas-Banda')

%Plotar atraso de grupo
figure
grpdelay(NUMp,DENp)
title('Atraso de Grupo - Passas-Banda')

%polos e zeros
figure
zplane(NUMp,DENp)
title('Polos e zeros - Passas-Banda')

%Verificar Requisitos 
var = (pi/10000);
var1 = ceil(wp(1)/var+1);
var2 = ceil(wp(2)/var+1);
var3 = ceil(wr(1)/var+1);  
var4 = ceil(wr(2)/var+1);  

fprintf('\n--- PASSA-BANDA ---\n')

%w = 0
mod_0 = 20*log10(abs(H(1)))

%w = wp1
mod_wp1 = 20*log10(abs(H(var1)))

%w = wp2
mod_wp2 = 20*log10(abs(H(var2)))

%w = wr1
mod_wr1 = 20*log10(abs(H(var3)))

%w = wr2
mod_wr2 = 20*log10(abs(H(var4)))


% 4 - Filtro rejeita-banda
%Frequências digitais
wp = 2*pi*[brfi brffs]/fa;
wr = 2*pi*[brfis brff]/fa;

%Pré-distorção das frequências
Wap = 2*fa*tan(wp/2);
War = 2*fa*tan(wr/2);

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
[NUMr,DENr] = bilinear(bt3,at3,fa);

% Determina H(z)
hr = tf(NUMr, DENr, -1, 'variable','z^-1');

%Plotar Resposta em Frequencia
w = 0:pi/10000:pi;
H = freqz(NUMr,DENr,w);

%Plotar módulo e fase
figure
freqz(NUMr,DENr)
title('Gráfico de módulo e fase - Rejeita-Banda')

%Plotar atraso de grupo
figure
grpdelay(NUMr,DENr)
title('Atraso de Grupo - Rejeita-Banda')

%polos e zeros
figure
zplane(NUMr,DENr)
title('Polos e zeros - Rejeita-Banda')

%Verificar Requisitos 
var = (pi/10000);
var1 = ceil(wp(1)/var+1);
var2 = ceil(wp(2)/var+1);
var3 = ceil(wr(1)/var+1);  
var4 = ceil(wr(2)/var+1);  

fprintf('\n--- REJEITA-BANDA ---\n')

%w = 0
mod_0 = 20*log10(abs(H(1)))  

%w = wp1
mod_wp1 = 20*log10(abs(H(var1)))  

%w = wp2
mod_wp2 = 20*log10(abs(H(var2))) 

%w = wr1
mod_wr1 = 20*log10(abs(H(var3)))  

%w = wr2
mod_wr2 = 20*log10(abs(H(var4)))


%{
c) Testar a saída de cada filtro individualmente alterando o valor dos ganhos
(G1, G2, G3 e G4), de "1" para "0" ou de "0" para "1".
%}

%Filtragem do sinal de áudio
y1 = filter(NUMb,DENb,x(:,1)); %Passa-Baixas
y2 = filter(NUMa,DENa,x(:,1)); %Passa-Altas
y3 = filter(NUMp,DENp,x(:,1)); %Passa-Banda
y4 = filter(NUMr,DENr,x(:,1)); %Rejeita-Banda

%Ganhos dos filtros
G1 = 1;
G2 = 0;
G3 = 0;
G4 = 0;

%Sinal de saída
yt = G1*y1 + G2*y2 + G3*y3 + G4*y4;

%sound(yt,fa)
figure
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

%%TODO
%validar Amax e a min
%pegar uma amostra em determinada frequencia para validar atenuações

