## This is the user-script for plotting using gleaner tool.

import sys
import os
# Path to gleaner (Better use environment variable PYTHONPATH!)
glrPath = os.getenv('HOME')+'/apes/gleaner'

## Import all required modules
import matplotlib.ticker as mtick
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
dbname = 'track.db'
# load database if exist else load tracking files and add to database
if os.path.isfile(dbname):
  print ('Processing data from existing database')
#  os.remove(dbname)
  import sqlite3
  sqlcon = sqlite3.connect(dbname)
else:
  print ('Processing data from tracking files')

  ftimes = []
  for rf in resfiles:
    m = re.search('tracking/.*_t(?P<time>.*).res', rf)
    ftimes.append((float(m.group('time')), rf))

  sortfiles = sorted(ftimes, key=itemgetter(0))
  last_ftime = sortfiles[-1][1].split('_')[-1]
  print ('Processing time file: *'+last_ftime)

  sqlcon = gleaner.tracking_to_db(fname = ['tracking/*hline_p*'+last_ftime], \
                                  dbname=dbname, tabname='hline')
## -------------------------------------------------------------------------- ##
print ('Normalized pressure over center axis:')
fig = mplt.figure()
ax = fig.add_subplot(111)
# Plot x, y ... at certain time step
# Simulation result
get_data_for_cols = ['coordX','normalized_pressure']
[x, y] = gleaner.get_columns(sqlcon, tabname='hline', \
                             columns=get_data_for_cols)
x, y = zip(*sorted(zip(x,y))) # sort of needed
mplt.plot(x, y, '-', color = 'r', label = 'Pressure')

mplt.axvline(x=nozzle_inner_dia_X, ls='-', color = 'b', label = 'x='+str(nozzle_inner_dia_X))

# plot setting
mplt.legend(loc=3, ncol=1,borderaxespad=0, \
            prop={'size':font_size}).get_frame().set_lw(0.0)
mplt.xlabel('x (m)')
mplt.ylabel('Normalized pressure ($N/m^2$)')
mplt.grid(True,which="major",ls="-")
ax.yaxis.set_major_formatter(y_formatter)

# save fig
figsize = [8,6]
fig = mplt.gcf()
fig.set_size_inches(figsize[0],figsize[1])
mplt.savefig('pressureOverCenterAxis.png', dpi=100, format='png', \
             bbox_inches="tight",interpolation=None)
## -------------------------------------------------------------------------- ##
print ('Velocity X over center axis:')
fig = mplt.figure()
ax = fig.add_subplot(111)
# Plot x, y ... at certain time step
# Simulation result
get_data_for_cols = ['coordX','velocity_phy_01']
[x, y] = gleaner.get_columns(sqlcon, tabname='hline', \
                             columns=get_data_for_cols)
x, y = zip(*sorted(zip(x,y))) # sort of needed
mplt.plot(x, y, '-', color = 'r', label = 'Velocity X')

mplt.axvline(x=nozzle_inner_dia_X, ls='-', color = 'b', label = 'x='+str(nozzle_inner_dia_X))

# plot setting
mplt.legend(loc=2, ncol=1,borderaxespad=0, \
            prop={'size':font_size}).get_frame().set_lw(0.0)
mplt.xlabel('x (m)')
mplt.ylabel('Velocity X ($m/s$)')
mplt.grid(True,which="major",ls="-")
ax.yaxis.set_major_formatter(y_formatter)

# save fig
figsize = [8,6]
fig = mplt.gcf()
fig.set_size_inches(figsize[0],figsize[1])
mplt.savefig('velocityXOverCenterAxis.png', dpi=100, format='png', \
             bbox_inches="tight",interpolation=None)
## -------------------------------------------------------------------------- ##
print ('Velocity Y over center axis:')
fig = mplt.figure()
ax = fig.add_subplot(111)
# Plot x, y ... at certain time step
# Simulation result
get_data_for_cols = ['coordX','velocity_phy_02']
[x, y] = gleaner.get_columns(sqlcon, tabname='hline', \
                             columns=get_data_for_cols)
x, y = zip(*sorted(zip(x,y))) # sort of needed
mplt.plot(x, y, '-', color = 'r', label = 'Velocity Y')

mplt.axvline(x=nozzle_inner_dia_X, ls='-', color = 'b', label = 'x='+str(nozzle_inner_dia_X))

# plot setting
mplt.legend(loc=2, ncol=1,borderaxespad=0, \
            prop={'size':font_size}).get_frame().set_lw(0.0)
mplt.xlabel('x (m)')
mplt.ylabel('Velocity Y ($m/s$)')
mplt.grid(True,which="major",ls="-")
ax.yaxis.set_major_formatter(y_formatter)

# save fig
figsize = [8,6]
fig = mplt.gcf()
fig.set_size_inches(figsize[0],figsize[1])
mplt.savefig('velocityYOverCenterAxis.png', dpi=100, format='png', \
             bbox_inches="tight",interpolation=None)
## -------------------------------------------------------------------------- ##

logging.info('Plots created')
