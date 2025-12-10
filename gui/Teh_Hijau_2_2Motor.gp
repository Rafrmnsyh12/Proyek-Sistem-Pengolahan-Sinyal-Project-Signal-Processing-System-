
set title "E-Nouse Data: Teh_Hijau_2_2Motor"
set xlabel "Time (s)"
set ylabel "Sensor Value"
set grid
set key outside
set term wxt size 1000,600 persist
plot "Teh_Hijau_2_2Motor.dat" using 1:2 with lines title "CO (M)" lc rgb "#FF5252" lw 2, \
     "Teh_Hijau_2_2Motor.dat" using 1:3 with lines title "Eth (M)" lc rgb "#448AFF" lw 2, \
     "Teh_Hijau_2_2Motor.dat" using 1:4 with lines title "VOC (M)" lc rgb "#69F0AE" lw 2, \
     "Teh_Hijau_2_2Motor.dat" using 1:5 with lines title "NO₂ (G)" lc rgb "#FFEB3B" lw 2, \
     "Teh_Hijau_2_2Motor.dat" using 1:6 with lines title "Eth (G)" lc rgb "#E040FB" lw 2, \
     "Teh_Hijau_2_2Motor.dat" using 1:7 with lines title "VOC (G)" lc rgb "#FFAB40" lw 2, \
     "Teh_Hijau_2_2Motor.dat" using 1:8 with lines title "CO (G)" lc rgb "#FFFFFF" lw 2
pause mouse close
