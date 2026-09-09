% 1 - xt transforme para tempo discreto
% amostragem do sinal x(nTs)
% Ts = período de amostragem, que é igual a Ts = 1/s.
% Definir um sinal x(t) com no minimo, 3 tons (f1, f2, f3);
% Plotar x(t) e x(n), na mesma tela

clc
clear all
close all

fs = 3000;
t = linspace(0, pi, 100000);

f1 = 440; 
f2 = 660; 
f3 = 1144;
xt = 2*cos(2*pi*f1*t) + sin(2*pi*f2*t) + 3*cos(2*pi*f3*t);

n = 0:3000;

ts = 1/fs;
xn = 0.5*cos(2*pi*f1*n*ts) + sin(2*pi*f2*n*ts) + 0.8*sin(2*pi*f3*n*ts);

figure(1)
subplot(2,1,1)
plot(t, xt, 'cyan', 'LineWidth', 0.5)
xlim([0 0.05])
set(gca, 'Color', 'black')
title('Sinal Continuo x(t)', 'Color', 'b')

subplot(2,1,2)
stem(n*ts, xn, 'green', 'LineWidth', 0.5)
xlim([0 0.05])
set(gca, 'Color', 'black')
title('Sinal Discreto x[n]', 'Color', 'b') 
