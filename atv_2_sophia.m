%% A 
%{
Prática 2
 Tempo discreto de duas sequências
Vetor a e vetor b
Vetor y com a convolução de a e b
Comando Stem para visualizar a,b e y
%}

size_conv = 0:10;
size_a = 0:5;
size_b = 0:5;

a = [2;3;5;7;8;9];
b = [1;1;1;1;1;1];

y = conv(a,b);

figure(1);

subplot(3,1,1);
stem(size_a, a);
title('Vetor a');

subplot(3,1,2);
stem(size_b, b);
title('Vetor b');

subplot(3,1,3);
stem(size_conv,y);
title('Saída y');

%% B
%{
Calcular resposta a impulso de um sistema inicialmente relaxado

Equação -> y(n) + (1/3)y(n-1) = x(n) + (1/2)x(n-1)
Transformada Z ->  Y(Z)* (1 + (1/3)*Z^-1) = x(z)*(1 + (1/2)*z^-1)
H(Z) = Y(Z)/X(Z) =  (1 + (1/2)*z^-1) /(1 + (1/3)*Z^-1)

Função impz visualizar vetor saida h
%}

num = [1 1/2]; % Y(Z)
den = [1 1/3]; % X(Z)

[H,T] = impz(num, den, 10);

figure(2)
stem(T,H);
title('Resposta ao impulso');

%% C
%{
Calcular sinal X(n) = 5e^jOmegan, Omega = 0,05pi e 0<= n <=100.
Apresentar dois gráficos, parte real e imaginária, sobrepostos com cores
distintas
%}
Omg = 0.05*pi;
n=0:100;
Xn = 5 * exp(1i * Omg * n);

figure(3)
hold on
plot(n, real(Xn), 'b')
plot(n, imag(Xn), 'r--')
legend('Real', 'Imaginária')
title('Real / Imaginária')
hold off

axis([0 100 -6 6])
title('Parte Real e Imaginária de X(n)')
xlabel('n')
ylabel('Amplitude')

figure(4)
subplot(2,1,1)
plot(n, abs(xn), 'b')
title('Modulo')

subplot(2,1,2)
plot(n, angle(xn), 'r')
title('Fase')

%% D
%{
Mesmos requisitos mas a função agora é 
X(n)= 5 r^n e ^jOmegan
Omega = 0,05pi, r = 0,95, n = 0 a 100;
%}

Omg_d = 0.05*pi;
n_d=0:100;
r_d = 0.95;
Xn_d = 5*(r_d.^n_d).*exp(1i * Omg_d * n_d);

figure(5)
hold on
plot(n_d, real(Xn_d), 'b')
plot(n_d, imag(Xn_d), 'r--')
legend('Real', 'Imaginária')
title('Real / Imaginária')
hold off

axis([0 100 -6 6])
title('Parte Real e Imaginária de X(n)')
xlabel('n')
ylabel('Amplitude')

figure(6)
subplot(2,1,1)
plot(n_d, abs(Xn_d), 'b')
title('Modulo')

subplot(2,1,2)
plot(n_d, angle(Xn_d), 'r')
title('Fase')
