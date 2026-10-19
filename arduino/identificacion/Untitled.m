clear;
clc;
close all;

%% ========================================================
%  DATOS DEL ENSAYO
% =========================================================

datos = readmatrix('datos_pwm102_derecho.csv');

t = datos(:,1) / 1000;   % ms -> segundos
rpm = datos(:,2);

%% ========================================================
%  GRAFICA DE LA RESPUESTA REAL
% =========================================================

figure;

plot(t, rpm, 'LineWidth', 1.5);
grid on;

xlabel('Tiempo [s]');
ylabel('RPM');
title('Respuesta al escalón - Motor A');