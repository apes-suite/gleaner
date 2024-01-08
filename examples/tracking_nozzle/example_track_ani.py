## This is the user-script for plotting using gleaner tool.
import sys
import os
# Path to gleaner (Better use environment variable PYTHONPATH!)
glrPath = os.getenv('HOME')+'/apes/gleaner'

## Import all required modules
import matplotlib.pyplot as mplt
sys.path.append(glrPath)
import gleaner
import logging

# font setting
from matplotlib import rc
font_size = 12
font_family = 'serif'
font_type = 'Times New Roman'
rc('text',usetex=True)
font = {'family':font_family,'%s'%font_family:font_type,'size':font_size}
rc('font',**font)

#axis without scientific notation
import matplotlib.ticker as mtick
y_formatter = mtick.ScalarFormatter(useOffset=False)

## -------------------------------------------------------------------------- ##
logging.basicConfig(level=logging.INFO)
## -------------------------------------------------------------------------- ##
from subprocess import Popen, PIPE
# Simulation parameters
simfile = 'common.lua'
nozzle_inner_dia_X = float(Popen(['lua', '-e',"dofile '"+simfile+"'; \
                           print(string.format('%.2E',nozzle_inner_dia_X))"],\
                           stdout=PIPE).communicate()[0].decode('ascii'))

## -------------------------------------------------------------------------- ##
logging.info('Started creating plots ...') 
 
import glob
import re
from operator import itemgetter
resfiles = glob.glob('tracking/*hline_p00000_*.res')

# data base filename
dbname = 'track_ani.db'
nFrames = 100
if os.path.isfile(dbname):
  print ('Processing data from database file: '+dbname)
#  os.remove(dbname)
  import sqlite3
  sqlcon = sqlite3.connect(dbname)
else:
  print ('Processing data from tracking files')

  ftimes = []
  for rf in resfiles:
    m = re.search('tracking/.*hline_p00000_t(?P<time>.*).res', rf)
    print('m: ',m)
    timestr = rf.split('_')[-1]
    ftimes.append((float(m.group('time')), timestr, rf))

  sortfiles = sorted(ftimes, key=itemgetter(0))
  #last_ftime = sortfiles[-1][1].split('_')[-1]
  #print ('Processing time file: *'+last_ftime)

  #for itime in range(len(sortfiles)):
  interval = len(sortfiles)/nFrames
  for itime in range(nFrames):
    timestr = sortfiles[int(itime*interval)][1] 
    print(itime, itime*interval, timestr)
    # Load text, dump into a database with specific tabname to get columns later
    sqlcon = gleaner.tracking_to_db(fname = ['tracking/*hline_p*'+timestr], \
                                    dbname=dbname, tabname='hline'+str(itime))
# -------------------------------------------------------------------------- ##
# Animation for all time steps
logging.info('Started creating animation ...')
funcAnimation = False

from matplotlib import animation
# Set up formatting for the movie files
Writer = animation.writers['ffmpeg']
writer = Writer(fps=10, metadata=dict(artist='Me'), bitrate=1800)

fig = mplt.figure()
ax = fig.add_subplot(111)
mplt.grid(True)
mplt.xlabel('x (m)')
mplt.ylabel('Normalized pressure ($N/m^2$)')
mplt.grid(True,which="major",ls="-")
ax.yaxis.set_major_formatter(y_formatter)

get_data_for_cols = ['coordX','normalized_pressure']

if funcAnimation == True:
  line, = ax.plot([], [], lw=1)
  x1 = [nozzle_inner_dia_X]*2
  y1 = [-4.0, 4.0]
  def init():
    line.set_data(x1,y1)
    return line

  def animate(i):
    [x, y] = gleaner.get_columns(sqlcon, tabname='hline'+str(i), \
                                 columns=get_data_for_cols)
    x, y = zip(*sorted(zip(x,y))) # sort of needed
    line.set_data(x,y)
    if i >= (nFrames/2):
      ax.set_ylim(-0.25,0.25)
    elif i >= (nFrames/4) and i < (nFrames/2):
      ax.set_ylim(-0.5,0.5)
    else:  
      ax.set_ylim(-2.0,2.0)

    return line

  anim = animation.FuncAnimation(fig, animate, frames=nFrames, init_func=init)
  anim_file = 'pressure_funAnim.mp4'
else:
  hline = []
  for iplt in range(nFrames):
    [x, y] = gleaner.get_columns(sqlcon, tabname='hline'+str(iplt), \
                                 columns=get_data_for_cols)
    x, y = zip(*sorted(zip(x,y))) # sort of needed
    if iplt == 0:
      hline.append(mplt.plot(x, y, '-', color = 'r', label = 'Pressure'))
    else:
      hline.append(mplt.plot(x, y, '-', color = 'r'))

  anim = animation.ArtistAnimation(fig, hline, interval=50, repeat_delay=3000, \
                                   blit=True)
  anim_file = 'pressure_artistAnim.mp4'

anim.save(anim_file, writer=writer)
#mplt.show(True)
logging.info('Animation created')  

logging.info('Plots created')
