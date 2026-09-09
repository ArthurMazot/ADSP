clc
clear all
close all

%%Parte 1
% A) e B)
[x, fs]  = audioread('Bagatelle-no.-25-__Für-Elise___-WoO-59.wav');

bCall = x(:,1);
tb = (0:1/fs:(length(bCall)-1)/fs);


figure(1)
plot(tb, bCall)
xlim([0 tb(end)])
xlabel('Tempo (segundos)')
ylabel('Amplitude')
title('{\bf Audio}')

%sound(bCall, fs);

% C)

m = length(bCall); %
n = pow2(nextpow2(m)); %Corrige para a próxima potencia de 2

y = fft(bCall, n);
f = (0:n-1)*(fs/n);
p = y.*conj(y)/n;
p = p./max(p);

figure(2)
subplot(2,1,1)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlabel('Frequência (Hz)')

subplot(2,1,2)
plot(f(1:floor(n/2)), angle(y(1:floor(n/2))))

% D) e E)

bCallCos = bCall + 0.02*cos(2*pi*4000*tb)';

m = length(bCallCos); %
n = pow2(nextpow2(m)); %Corrige para a próxima potencia de 2

y = fft(bCallCos, n);
f = (0:n-1)*(fs/n);
p = abs(y)/n;
p = p./max(p);

figure(3)
subplot(2,1,1)
plot(f(1:floor(n/2)), p(1:floor(n/2)))
xlabel('Frequência (Hz)')

subplot(2,1,2)
plot(f(1:floor(n/2)), angle(y(1:floor(n/2))))

%% Parte 2)
% A)
[x, fs] = audioread("Eagles ft. Flashdance - Hotel california.mp3");

% B)
vet = 2*rand([length(x), 2]); %Vetor de numeros aleatórios entre 0 e 2, sendo "vet" uma matriz de tamanho length(x) por 2
%sound(x.*vet, fs);

% C)
%sound(x, fs/2) %fs/2 deixa a musica mais lenta
%sound(x, fs*2) %fs*2 deixa a musica mais rapida

% D)
y = flipud(x);
figure(5)
plot(y)
%sound(y, fs)
audiowrite("HotelCaliforniaFliped.wav", y, fs)

% F)
if length(x(1)) ~= length(x(2))
    return
end

% G)
left = x(:,1);
right = x(:, 2);

% H)
semVoz = right - left;

% I)
figure(4)
subplot(2,2,1)
plot(x)
title("Original")

subplot(2,2,2)
plot(left)
title("Esquerda")

subplot(2,2,3)
plot(right)
title("Direita")

subplot(2,2,4)
plot(semVoz)
title("Sem voz")

% J)
%sound(semVoz, fs)
audiowrite("HotelCaliforniaSemVoz.wav", semVoz, fs)