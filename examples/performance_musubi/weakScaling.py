## This is an example user-script for plotting performance data using the
## gleaner module.

# Path to gleaner (Better use environment variable PYTHONPATH!)
import matplotlib.pyplot as mplt
import numpy as np
import sys
import os
home = os.getenv('HOME')
sys.path.append(home+'/apes/gleaner')

from matplotlib import rc
rc('text',usetex=True)
font_size = 20
font_family='sans-serif'
font_type='sans-serif'
font = {'family':font_family,'%s'%font_family:font_type,'size':font_size}
rc('font',**font)

figsize = [8,6]

# Import all required modules
import gleaner

import logging

print('Scaling analysis for Musubi')

## -------------------------------------------------------------------------- ##
# Clean the log file
log_file = 'bgk.log'
with open(log_file, 'w'):
    pass

logging.basicConfig(filename=log_file, level=logging.INFO)#, \
             #format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

## -------------------------------------------------------------------------- ##
# Load text, dump into a database, get back the desired columns
sqlcon = gleaner.timing_to_db( fname  = 'timing_bgk_cray.res',
                               dbname = 'timing.db',
                               tabname = 'timings' )

# Obtain x-y data from the database, dump into a file or on screen
import math  

# Scaling Plots
logging.info('Established connection to database')                    
perfmap, ID_tuple = gleaner.perfmap_series(sqlcon = sqlcon, tabname = 'timings',
                  signature = ['Revision', 'SimName', 'nProcs', 'DomSize'],
                  xcol = 'DomSize', ycol = 'MLUPs')

sqlcon.close()

#print('ID_tuple ', ID_tuple)                  
#print('perfmap ', perfmap)          
logging.info('Checking for WEAK and weak scaling and efficicency ...')  
                             
for key, series in perfmap.items():
#  print('Key :',key)
#  print('nProc :[DomSize, Performance]')
#  for nproc in sorted(series):
#     print("{0}: {1} ".format(nproc, series[nproc]))

  weak_table = gleaner.weak_efficiency( perfmap       = series,
                                        size_per_node = 8388608,
                                        ppn           = 24,
                                        min_nodes     = 2 )
  if weak_table != None:
    print("weak Scaling with 8388608 elements:")
    x=[]
    y=[]
    for nn, eff in weak_table:
      print("  {0} {1}".format(nn, eff))
      x = np.append(x, nn)
      y = np.append(y, eff*100)

  mplt.plot(x, y, '-bo', linewidth=3.0, label='8,388,608 elements/node')
     
mplt.ylim(0, 110)
mplt.xlim(1, 4096)
mplt.grid(True,which="major",ls="-")
mplt.grid(True,which="minor",ls="-")
mplt.legend(loc=4, ncol=1,\
            borderaxespad=0,prop={'size':16})
mplt.xscale('log')
mplt.xlabel('\\textbf{Number of nodes}')
mplt.ylabel('\\textbf{Parallel Efficiency (\%)}')
fig = mplt.gcf()
fig.set_size_inches(figsize[0],figsize[1])
mplt.savefig('weakScaling_cube.pdf', dpi=100, format='pdf',bbox_inches="tight",interpolation=None)
mplt.show()
logging.info('Done checking')                          
logging.info('Finished')
