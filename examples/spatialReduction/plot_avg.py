## This is the user-script for plotting using gleaner tool.
import sys
import os

# Path to gleaner (Better use environment variable PYTHONPATH!)
if os.path.exists( os.getenv('HOME')+'/apes/gleaner'): 
  glrPath = os.getenv('HOME')+'/apes/gleaner'
else:
  print('Gleaner library not found')
  exit

# Import gleaner module
sys.path.append(glrPath)
import gleaner
import logging
import numpy as np
import matplotlib.ticker as mtick
import matplotlib.pyplot as mplt
font_size = 12
#axis without scientific notation
y_formatter = mtick.ScalarFormatter(useOffset=False)
## -------------------------------------------------------------------------- ##
dbname = 'spatialRed.db'
column_red = 'Points_0'
in_file_centerline = 'sliceAtCenterLine.csv'
in_file_atX1_06D = 'sliceAtX1_06D.csv'
## -------------------------------------------------------------------------- ##
logging.basicConfig(level=logging.INFO)
logging.info('Started creating plots ...') 
if os.path.isfile(dbname):
  logging.info('Processing data from existing database')
#  os.remove(dbname)
  import sqlite3
  sqlcon = sqlite3.connect(dbname)
else:
  logging.info('Processing data from tracking files')

  logging.basicConfig(level=logging.INFO)
  sqlcon = gleaner.paraview_to_db(fname = [in_file_centerline], dbname = dbname,
                                  tabname = 'sliceAtCenterLine')

  sqlcon = gleaner.paraview_to_db(fname=[in_file_atX1_06D], dbname=dbname,
                                  tabname='sliceAtX1_06D')

  fieldnames = gleaner.get_paraview_header(in_file_centerline)
  gleaner.spatial_reduction_in_db(sqlcon, tabname = 'sliceAtCenterLine',
                                  columns = fieldnames,
                                  reduce_coord_column='Points_0')

  fieldnames = gleaner.get_paraview_header(in_file_atX1_06D)
  gleaner.spatial_reduction_in_db(sqlcon, tabname='sliceAtX1_06D',
                                  columns=fieldnames,
                                  reduce_coord_column='Points_1')
## -------------------------------------------------------------------------- ##
diameter = 0.0029055
u0 = 20.0772 
height =  30*diameter
cylinder_x = height/2.0 + diameter
cylinder_y = height/2.0
## -------------------------------------------------------------------------- ##
logging.info('velXAvg along center line:')
fig = mplt.figure()
ax = fig.add_subplot(111)
get_data_for_cols = ['Points_0', 'velocity_avg_0']
[coord, velX_avg] = gleaner.get_columns(sqlcon, tabname='sliceAtCenterLine_red',
                                        columns=get_data_for_cols, as_nparray=True)

normCoord = (coord - cylinder_x) / diameter
normVelX_avg = velX_avg / u0
normCoord, normVelX_avg = zip(*sorted(zip(normCoord, normVelX_avg)))

mplt.plot(normCoord, normVelX_avg)

mplt.xlabel('$x/D$')
mplt.ylabel('$u/u0$')
mplt.grid(True,which="major",ls="-")
ax.yaxis.set_major_formatter(y_formatter)
mplt.xlim(0.0,6.0)
mplt.ylim(-0.5,1)

figsize = [8,6]
fig = mplt.gcf()
fig.set_size_inches(figsize[0],figsize[1])
mplt.savefig('velXAvgAlongCenterLine.png', dpi=100, format='png',
             bbox_inches="tight")
## -------------------------------------------------------------------------- ##
logging.info('Reynolds stress streamwise along center line:')
fig = mplt.figure()
ax = fig.add_subplot(111)
get_data_for_cols = ['Points_0', 'velocity_avg_0', 're_stressX_avg_0']
[coord, velX_avg, velXSqr_avg] = gleaner.get_columns(sqlcon, tabname='sliceAtCenterLine_red',
                                                     columns=get_data_for_cols,
                                                     as_nparray=True)

normCoord = ( coord - cylinder_x ) / diameter
normVelX_avg = velX_avg/u0
normVelXSqr_avg = velXSqr_avg/u0**2

re_ns = normVelXSqr_avg - np.square(normVelX_avg)
normCoord, re_ns = zip(*sorted(zip(normCoord, re_ns)))

mplt.plot(normCoord, re_ns)

mplt.xlabel('$x/D$')
mplt.ylabel('$u\'u\'/u0^2$')
mplt.grid(True,which="major",ls="-")
ax.yaxis.set_major_formatter(y_formatter)
mplt.xlim(0.0,6.0)
mplt.ylim(0.0,0.12)

figsize = [8,6]
fig = mplt.gcf()
fig.set_size_inches(figsize[0],figsize[1])
mplt.savefig('ReynoldsStressXXAlongCenterLine.png', dpi=100, format='png',
             bbox_inches="tight")
## -------------------------------------------------------------------------- ##
logging.info('velXAvg along height:')
fig = mplt.figure()
ax = fig.add_subplot(111)
get_data_for_cols = ['Points_1', 'velocity_avg_0']
[coord, velX_avg] = gleaner.get_columns(sqlcon, tabname='sliceAtX1_06D_red',
                                        columns=get_data_for_cols,
                                        as_nparray=True)

normCoord = (coord - cylinder_y) / diameter
normVelX_avg = velX_avg / u0
normCoord, normVelX_avg = zip(*sorted(zip(normCoord, normVelX_avg)))

mplt.plot(normCoord, normVelX_avg)

mplt.xlabel('$y/D$')
mplt.ylabel('$u/u0$')
mplt.grid(True,which="major",ls="-")
ax.yaxis.set_major_formatter(y_formatter)
mplt.xlim(-1.5,1.5)

figsize = [8,6]
fig = mplt.gcf()
fig.set_size_inches(figsize[0],figsize[1])
mplt.savefig('velXAvgAtX1_06D.png', dpi=100, format='png',
             bbox_inches="tight")
## -------------------------------------------------------------------------- ##
logging.info('Reynolds stress streamwise along height:')
fig = mplt.figure()
ax = fig.add_subplot(111)
get_data_for_cols = ['Points_1', 'velocity_avg_0', 're_stressX_avg_0']
[coord, velX_avg, velXSqr_avg] = gleaner.get_columns(sqlcon, tabname='sliceAtX1_06D_red',
                                                     columns=get_data_for_cols,
                                                     as_nparray=True)

normCoord = ( coord - cylinder_y ) / diameter
normVelX_avg = velX_avg/u0
normVelXSqr_avg = velXSqr_avg/u0**2

re_ns = normVelXSqr_avg - np.square(normVelX_avg)
normCoord, re_ns = zip(*sorted(zip(normCoord, re_ns)))

mplt.plot(normCoord, re_ns)

mplt.xlabel('$y/D$')
mplt.ylabel('$u\'u\'/u0^2$')
mplt.grid(True,which="major",ls="-")
ax.yaxis.set_major_formatter(y_formatter)
mplt.xlim(-1.5,1.5)

figsize = [8,6]
fig = mplt.gcf()
fig.set_size_inches(figsize[0],figsize[1])
mplt.savefig('ReynoldsStressXXAtX1_06D.png', dpi=100, format='png',
             bbox_inches="tight")
## -------------------------------------------------------------------------- ##
mplt.show()
## -------------------------------------------------------------------------- ##