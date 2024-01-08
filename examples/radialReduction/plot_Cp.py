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
dbname = 'cylinderRe3900_Cp.db'
coord_col = ['coordX', 'coordY']
diameter = 0.0029055
u0 = 20.0772
height =  30*diameter
cylinder_x = height/2.0 + diameter
cylinder_y = height/2.0
## -------------------------------------------------------------------------- ##
logging.basicConfig(level=logging.INFO)
logging.info('Started creating plots ...')
logging.info('Processing data from existing database')
import sqlite3
sqlcon = sqlite3.connect(dbname)
cur = sqlcon.cursor()
fieldnames = ['coeffPressure']
gleaner.radial_reduction_in_db(sqlcon, tabname='Cp',
                               columns=fieldnames,
                               coord_column=coord_col,
                               geometry_pos = [cylinder_x, cylinder_y])
## -------------------------------------------------------------------------- ##
logging.info('Pressure coefficient on the cylinder:')
fig = mplt.figure()
ax = fig.add_subplot(111)
interval = 2
get_data_for_cols = ['theta', 'coeffPressure']
[theta, Cp_avg] = gleaner.get_columns(sqlcon, tabname='Cp_red', \
                                      columns=get_data_for_cols)

nPoints = len(theta) / interval
theta_new = []
Cp_avg_new = []
for ii in range(0, len(theta), interval):
  theta_new.append(theta[ii])
  Cp_avg_new.append(Cp_avg[ii])

theta_new, Cp_avg_new = zip(*sorted(zip(theta_new, Cp_avg_new)))

logging.info('base pressure coefficient: ' + str(np.max(Cp_avg_new)))
mplt.plot(theta_new, Cp_avg_new, 'o', color='k')

mplt.xlabel('$\\theta$')
mplt.ylabel('$C_p$')
mplt.grid(True, which="major", ls="-")
ax.yaxis.set_major_formatter(y_formatter)
mplt.xlim(0.0, 180.0)
# mplt.ylim(-0.5,1)

# save fig
mplt.legend(loc=1, ncol=1, borderaxespad=0, \
            prop={'size': font_size}).get_frame().set_lw(0.0)
figsize = [8, 6]
fig = mplt.gcf()
fig.set_size_inches(figsize[0], figsize[1])
mplt.savefig('pressureCoeffOverAngle.png', dpi=100, format='png', \
             bbox_inches="tight")
## -------------------------------------------------------------------------- ##
mplt.show()
## -------------------------------------------------------------------------- ##
