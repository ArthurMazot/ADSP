fc = 0.3; [h,w]=freqz (fir1 (50, fc,'high', hann(51)));
plot(w/pi,20*log10(abs(h)))