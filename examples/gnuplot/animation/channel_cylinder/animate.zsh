#!/bin/bash
#
# This file does the following (after making it executable):
#
# - for each time step combines the files from all processors to one single file
# - sends commands to GNUPLOT that itself creates EPS plots
# - converts those to PDF and to PNG
# - creates GIF animation
# - deletes all plots (PNG,PDF,EPS) cause only the GIF is needed
#
# To test this script copy it to ~/apes/gleaner/examples/animation/channel_cylinder/
# because the result files are located there.
#
echo
echo 'Removing pics dir and creating pics dir'
rm -r pics
mkdir pics
echo 'Done'
echo
echo 'Combining and renaming tracking files'
for i in tracking/L*_vel_global_p*_t*.res
do 
  export files=${i#*vel_global*_t}
  cat ${i} >> tracking/L${LEVEL}_vel_combined_t${files}
done
echo 'Creating Plots with GNUPLOT'
for j in tracking/*vel_combined_t*
do
  export name=${j#*vel_combined_t*}
  export vel_g_pic=pics/${name}.eps
  export vel_g_file=${j}
  echo $vel_g_file
  #
  # Here is the Gnuplot script
  #
  gnuplot << EOF
    # set line style
    set style line 1 lt -1 pt 6 ps 3 # black solid point
    set style line 2 lt -1 lw 1 # analytica style
    set style line 3 lt 0 lw 2
    set style line 4 lt 1 pt 6 ps 2 # red empty circle
    set style line 5 lt 3 pt 4 ps 2 # blue empty rectangle
    vel_g_pic=system("echo $vel_g_pic")
    vel_g_file=system("echo $vel_g_file")
    # plot global velocity 
    set terminal postscript eps size 16,4 enhanced color font 'Helvetica,25' linewidth 3
    #set terminal png size 400,300 enhanced font 'Helvetica,25' linewidth 3
    set output vel_g_pic
    LABEL='${name}'
    set obj 1 rect at 1.5,0.15 size char strlen(LABEL)+1, char 1.5 fc rgb "white" fillstyle solid 1.0 front
    unset grid
    unset key
    set cbrange [0:0.003]
    set palette model RGB defined (0 "blue", 1 "green",2 'red')
    set title 'Velocity vector distribution'
    set cblabel 'normalized velocities'
    set xlabel 'X'
    set ylabel 'Y'
    set label 1 LABEL at 1.5,0.15 front center
    plot vel_g_file using 1:2:(\$4/\$4*0.02):(\$5):(sqrt(\$4**2+\$5**2)) with vectors filled head size .5,.5 lw 1.0 palette 
EOF
#
# Here ends the Gnuplot script.
#
done
echo 'Done'
echo 'Going to pics folder'
cd pics
echo 'Start Converting to PDF'
echo
find *.eps -exec epspdf {} \;
echo 'Done'
echo
echo 'Start Converting to PNG'
echo
find *.pdf -exec pdftocairo -png {} \;
echo 'Done'
echo
echo 'Sort the files according to the time steps.'
sorted=($(find *.png | sort -t. -k 1,1n))
echo 'Here is the list:'
echo ${sorted[@]}
echo 
echo 'Start Converting to GIF'
convert -delay 0.15 ${sorted[@]} animation.gif
echo 
echo 'Done'
echo 
echo 'Delete PNGs PDFs and EPSs from pics folder'
rm ./*.pdf
rm ./*.eps
rm ./*.png
echo 
echo 'The GIF is located inside ./pics/'
echo 'FINISHED'
