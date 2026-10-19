clear;
clc;
close all;

%% ========================================================
% DATOS DEL ENSAYO
% =========================================================

datos = readmatrix('datos_pwm102_derecho.csv');

t = datos(:,1) / 1000;   % ms -> segundos

% Convertir RPM a positivas
rpm = abs(datos(:,2));

PWM = 150;

%% ========================================================
% GRAFICA DE LA RESPUESTA REAL
% =========================================================

figure;

plot(t, rpm, 'LineWidth', 1.5);
grid on;

xlabel('Tiempo [s]');
ylabel('RPM');
title('Respuesta al escalón - Motor A');

%% ========================================================
% RPM FINAL
% =========================================================

% Promedio de las últimas 20 muestras
rpm_final = mean(rpm(end-19:end));

%% ========================================================
% GANANCIA
% =========================================================

K = rpm_final / PWM;

%% ========================================================
% CONSTANTE DE TIEMPO
% =========================================================

rpm_63 = 0.632 * rpm_final;

indice_tau = find(rpm >= rpm_63, 1, 'first');

tau = t(indice_tau);

%% ========================================================
% MOSTRAR RESULTADOS
% =========================================================

fprintf('\n==============================\n');
fprintf('IDENTIFICACION MOTOR\n');
fprintf('==============================\n');

fprintf('PWM              = %.2f\n', PWM);
fprintf('RPM final        = %.2f RPM\n', rpm_final);
fprintf('Ganancia K       = %.4f RPM/PWM\n', K);
fprintf('Tau              = %.4f s\n', tau);

fprintf('\nFuncion de transferencia:\n');
fprintf('G(s) = %.4f / (%.4f*s + 1)\n', K, tau);

%% ========================================================
% MODELO DE PRIMER ORDEN
% =========================================================

num = K;
den = [tau 1];

G = tf(num, den);

disp(' ');
disp('Funcion de transferencia MATLAB:');
G

%% ========================================================
% RESPUESTA DEL MODELO
% =========================================================

rpm_modelo = rpm_final * (1 - exp(-t/tau));

%% ========================================================
% COMPARACION REAL VS MODELO
% =========================================================

figure;

plot(t, rpm, 'LineWidth', 1.5);
hold on;

plot(t, rpm_modelo, '--', 'LineWidth', 1.5);

grid on;

xlabel('Tiempo [s]');
ylabel('RPM');

title('Motor A - Respuesta real vs modelo');

legend('Datos reales', ...
       'Modelo de primer orden', ...
       'Location', 'southeast');