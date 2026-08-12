clc
clear all
close all

fs = 3000;
t = linspace(0, pi, 100000);

f1 = 440; f2 = 660; f3 = 1144;
xt = 0.5*cos(2*pi*f1*t) + sin(2*pi*f2*t) + 0.8*sin(2*pi*f3*t);

n = 0:3000;

ts = 1/fs;
xn = 0.5*cos(2*pi*f1*n*ts) + sin(2*pi*f2*n*ts) + 0.8*sin(2*pi*f3*n*ts);

figure(1)
subplot(2,1,1)
plot(t, xt)
xlim([0 0.05])

subplot(2,1,2)
stem(n*ts, xn)
xlim([0 0.05])
