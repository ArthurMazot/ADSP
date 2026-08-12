clc
clear all
close all

Fs = 3000;
f1 = 440; f2 = 660; f3 = 1144;


%% A)
ny = 0:14;
na = 0:7;
nb = 0:7;
a = [1 2 3 4 5 6 7 8];
b = [1 1 1 1 1 1 1 1];

y = conv(a, b);
figure(1)
subplot(3,1,1)
stem(na, a)
title('A')

subplot(3,1,2)
stem(nb, b)
title('B')

subplot(3,1,3)
stem(ny, y)
title('Y')

%% B)
den = [1 1/2];
num = [1 1/3];

[H, T] = impz(num, den, 10);

figure(2)
stem(T,H);
