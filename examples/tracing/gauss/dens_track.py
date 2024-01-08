## This is the user-script for plotting using gleaner tool.

# Path to gleaner (Better use environment variable PYTHONPATH!)
import sys
import os
sys.path.append('../../')

glrPath = os.getenv('HOME')+'/apes/gleaner'
sys.path.append(glrPath)
## Import all required modules
import matplotlib.pyplot as mplt
import gleaner
import logging

## ------------------------------------------------------------------------------------- ##
# Clean the log file
log_file = 'euler.log'
with open(log_file, 'w'):
    pass

logging.basicConfig(filename=log_file, level=logging.INFO)#, \
             #format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

## ------------------------------------------------------------------------------------- ##

## Enter the list of file name(s) (wild-cards are allowed)
fname = []
fname.append('tracking/Gaussian_pulse_validation_line_p00000_t1.000E+00.res')#tracking/crvp__lineX_average_l4_p00000_t0.000E+00.res')

## ------------------------------------------------------------------------------------- ##
# This is an example setup in accordance to the "bgk_timing.res" data file, 
# a default setup is yet to be designed 

logging.info('Started creating plots ...') 
 
print ('Processing data from tracking files')

# Load text, dump into a database, get back the desired columns
get_data_for_cols = ['coordX','density']
sqlcon = gleaner.tracking_to_db(fname, dbname='dens.db', tabname='density')
[x, y] = gleaner.get_columns(sqlcon, tabname='density', columns=get_data_for_cols)

#x, y = zip(*sorted(zip(x,y))) # sort of needed
# Plot x, y, z ... at certain time step
mplt.plot(x, y)
mplt.xlabel (get_data_for_cols[0])
mplt.ylabel (get_data_for_cols[1])
mplt.grid   (True)
mplt.show   (True)
logging.info('Plots created')

# Animation for all time steps

logging.info('Started creating animation ...')
import matplotlib.pylab as mplab
from matplotlib import animation
import glob 
import re
from operator import itemgetter

resfiles = glob.glob('./tracking/*validation_line*.res')

ftimes = []
for rf in resfiles:
  m = re.search('tracking/.*_t(?P<time>.*).res', rf)
  ftimes.append((float(m.group('time')), rf))

sortfiles = sorted(ftimes, key=itemgetter(0))

fig = mplt.figure()
ax = mplt.axes(xlim=(0,60), ylim=(3.7,4.5))
#ax.set_xticks([-1, -1+(2./6.), -2./6., 0, 2./6., 1-(2./6.), 1])
ax.xaxis.grid(True)
ax.yaxis.grid(True)
ax.set_xlabel('X')
ax.set_ylabel('density')  
line, = ax.plot([], [], lw=1)

def animate(i):
  state = mplab.loadtxt(sortfiles[i][1])
  x, y = zip(*sorted(zip(state[:,0], state[:,3])))
  line.set_data(x,y)
  return line

anim = animation.FuncAnimation(fig, animate, frames=len(sortfiles), interval=40)
anim.save('./density.mp4', writer="avconv", fps=5, bitrate=50)
mplt.show(True)
print ("Animation is saved in current working directory.")
logging.info('Animation created')  
logging.info('Finished')

