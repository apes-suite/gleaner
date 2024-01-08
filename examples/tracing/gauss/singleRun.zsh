#!/bin/bash
# Evaluate the current test case

musubi=~/apes/musubi/build/musubi
seeder=~/apes/seeder/build/seeder

# create folders and delete old results files
echo "Create directory and delete old files"
[ -d mesh ]     && rm mesh/*     || mkdir mesh
[ -d tracking ] && rm tracking/* || mkdir tracking
rm *.log
rm *.res
rm *.mp4
rm *.db

# run Seeder
${seeder} | tee ${seeder_log}

# run Musubi
${musubi} musubi.lua 

# run Gleaner
python3 dens_track.py
