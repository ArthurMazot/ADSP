close all     %fecha as janelas que est�o abertas
clear all     %apaga todas as vari�veis da mem�ria

Fs = 4000;      %frequ�ncia de amostragem 4kHz
F1 = 1000;      %1a frequ�ncia do sinal
F2 = 1100;      %2a frequ�ncia do sinal
F3 = 500;       %3a frequ�ncia do sinal
T=1/Fs;         %per�odo de amostragem
n = 10000;      %n�mero de amostras do sinal
mtm = (0:n)/(Fs);   %vetor de valores de tempo discreto
fq = Fs*(0:n)/n;    %vetor de frequ�ncias, para ajustar eixo x, no gr�fico da fft
xt = 3*cos(2*pi*F1*mtm) + 7*sin(2*pi*F2*mtm)+ cos(2*pi*F3*mtm); %sinal com 3 frequ�ncias
Xt = fft(xt);   %transformada de Fourier do sinal xt

%Processamento do Sinal - Filtragem
num = [1 0 1];  %coeficientes do numerador da H(z)
den = [1];      %coeficientes do denominador da H(z)

y = filter(num,den,xt); %Efetua a opera��o y(n)=x(n)-x(n-2) - Filtragem do sinal xt
Y = fft(y); %Transformada de Fourier da sa�da y(n) do filtro

na=0:10000; %vetor de valores de n
xa=3*cos(2*pi*F1/(Fs*100)*na)+7*sin(2*pi*F2/(Fs*100)*na)+cos(2*pi*F3/(Fs*100)*na); %sinal amostrado
n=0:100:length(na); %vetor de valores de n
h=sinc(-10:.01:10); %fun��o para reconstru��o sinal tempo cont�nuo
yaux=zeros(length(n),length(xt)+length(h)-1); %vetor de zeros
for i=1:length(n),
yaux(i,100*i-99:100*i-100+length(h))=h*y(i); %convolu��o da sa�da do filtro com h
end;
yc=sum(yaux);
ya=yc(1001:length(yc)-1000); %sinal de sa�da no tempo cont�nuo
Ta=1/400000;

plot(na*Ta,xa); %plota sinal original

figure
freqz(num,den); %resposta de m�dulo e fase do filtro

figure
plot(na*Ta,ya); %sinal de sa�da do filtro

figure
subplot(2,1,1)
plot(fq-1/(2*T),(fftshift(abs(Xt)))) %plota FFT do sinal de entrada
grid
xlabel('Frequ�ncia em Hz')
subplot(2,1,2)
plot(fq-1/(2*T),(fftshift(abs(Y)))) %plota fft do sinal de sa�da
grid
xlabel('Frequ�ncia em Hz')