"""
Gleaner animation example of velocity vector plots 
for all simulation's time steps from the test case
2D channel with cylinder. The number of arrows depends
either on the number of segments in the tracking part
of Musubi or on the given geometry level if tracking
shape is global.

The test case is located in:
apes/musubi/testsuite/validation/channel_cylinder/Re20/

One needs the result files: *vel_global_p*_t*.res
These contain all the time step data for velocity.

To create the animation one runs the script with: 
python3 vel_ani.py

This process takes a few (~10) minutes.
One can choose between animation and single plot and 
between GIF (bigger) and MP4 (smaller) if animation.

"""
## Choose if single plot or animation
single_plot =True
## Choose time step for single plot
time_step = 8

## Choose GIF or MP4 if GIF == False then MP4 == True
use_gif = True
## This is the user-script for plotting using gleaner tool.
import sys
import os
import operator
# Path to gleaner (Better use environment variable PYTHONPATH!)
glrPath = os.getenv('HOME')+'/apes/gleaner'

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
import glob
import re
from operator import itemgetter

# enter the file names of the tracking files here
resfiles = glob.glob('tracking/*vel_global_p*.res')

# data base filename
dbname = 'vel_ani.db'
nFrames = 100
if os.path.isfile(dbname):
  print ('Processing data from database file: '+dbname)
  import sqlite3
  sqlcon = sqlite3.connect(dbname)
else:
  print ('Processing data from tracking files')
  
  ftimes = []
  for rf in resfiles:
    # Name of resulting files
    # searching for a match
    m = re.search('tracking/.*_t(?P<time>.*).res', rf)
    #print('m: ',m)
    timestr = rf.split('_')[-1]
    #print('timestr: ',timestr)
    #print("float(m.group('time')): ",m.group('time'))
    ftimes.append((float(m.group('time')), timestr, rf))
  
  # files are sorted from first to last time step
  sortfiles = sorted(ftimes, key=itemgetter(0))
  #print('sortfiles: ',sortfiles)
  
  #for itime in range(len(sortfiles)):
  interval = len(sortfiles)/nFrames
  for itime in range(nFrames):
    timestr = sortfiles[int(itime*interval)][1] 
    print(itime, itime*interval, timestr)
    # Load text, dump into a database with specific tabname to get columns later
    sqlcon = gleaner.tracking_to_db(fname = ['tracking/*vel_global_p*'+timestr], \
                                    dbname=dbname, tabname='vel_vec'+str(itime))
# -------------------------------------------------------------------------- ##
from matplotlib import animation
if use_gif == False:
    # File name of the animation
    anim_file = 'vel_vecAnim.mp4'
    # Set up formatting for the movie files
    Writer = animation.writers['ffmpeg']
    writer = Writer(fps=10, metadata=dict(artist='Me'))#, bitrate=1800)
else:
    anim_file = 'vel_vecAnim.gif'
    writer = 'imagemagick'

fig = mplt.figure()

# sizing of the plots
w = 16
h = 6
dpi=100
fig.set_size_inches(w,h,True)
ax = fig.add_subplot(111)

# plot a cylinder inside of the channel
circle = mplt.Circle((0.0,0.0),0.05)
ax.add_patch(circle)

# axes formatting
ax.set_xlim(-0.20,1.8)
ax.set_ylim(-0.2,0.2)
# labels of the axes
mplt.xlabel('x (m)')
mplt.ylabel('y (m)')
mplt.axes().set_aspect('equal')
# used columns from the data base
get_data_for_cols = ['coordX', 'coordY', 'vel_norm_01', 'vel_norm_02']

# set up empty vector plot
line = ax.quiver([], [], [], [], cmap='jet', headlength=0.1, linewidth=0.1)

# colorbar options
m = mplt.cm.ScalarMappable(cmap=mplt.cm.jet)
# range of colorbar (min,max)
m.set_array([0.0,0.003])
# positioning of colorbar
# pad= distance from plot
# fraction= width of colorbar
cbar = mplt.colorbar(m,orientation='horizontal', fraction=0.06, pad=0.1)
cbar.set_label('velocity (m / s)')
# fits the layout
mplt.tight_layout()

# function for animation
def animate(i):
  # read columns from data base and store them as lists
  [x, y, u, v] = gleaner.get_columns(sqlcon, tabname='vel_vec'+str(i), \
                               columns=get_data_for_cols)
  # calculate the norm of the velocity vector for the arrow plots
  u = tuple((m*0.04,) for m in u)
  v = tuple((n*0.04,) for n in v)
  uu = tuple((j[0]**2,) for j in u)
  vv = tuple((k[0]**2,) for k in v)
  sum_uv = tuple(map(operator.add, u, v))
  # calculate the arrows' color 
  c = tuple(l[0]**0.5 for l in sum_uv)
  x, y, u, v, c = zip(*sorted(zip(x,y,u,v,c))) # sort of needed
  # Make vector plot as subplot
  ax.quiver(x, y, u, v, c, cmap='jet', linewidth=0.3)
  ax.title.set_text('Velocity plot\ntime step = '+str(i))

  return line

if single_plot == True:
  logging.info('Create single plot ...')
  animate(time_step)
  mplt.show(True)
  fig.savefig('time_'+str(time_step)+'.png',dpi=dpi)
  logging.info('\n Single Plot created \n')
else:
  # Animation for all time steps
  mplt.title('Velocity plot animation')
  logging.info('Started creating animation ...')
  # calls the animation function for each time step
  anim = animation.FuncAnimation(fig, animate, frames=nFrames, blit=False)
  #blit = true not working with quiver plot
  # Save the animation to disk
  anim.save(anim_file, writer=writer,dpi=dpi)
  logging.info('\n Animation created \n')  
