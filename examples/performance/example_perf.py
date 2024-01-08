## This is an example user-script for plotting performance data using the
## gleaner module.

# Path to gleaner (Better use environment variable PYTHONPATH!)
import sys
sys.path.append('../../')

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
sqlcon = gleaner.timing_to_db( fname  = 'bgk_timing.res',
                               dbname = 'timing.db',
                               tabname = 'timings' )

# Obtain x-y data from the database, dump into a file or on screen
import math  

# Scaling Plots
logging.info('Established connection to database')                    
perfmap, ID_tuple = gleaner.perfmap_series(sqlcon = sqlcon, tabname = 'timings',
                  signature = ['Revision', 'Casename', 'nProcs', 'DomSize'],
                  xcol = 'DomSize', ycol = 'MLUPs')

sqlcon.close()

#print('ID_tuple ', ID_tuple)                  
#print('perfmap ', perfmap)          
logging.info('Checking for WEAK and STRONG scaling and efficicency ...')  
                             
for key, series in perfmap.items():
  print('Key :',key)
  print('nProc :[DomSize, Performance]')
  for nproc in sorted(series):
     print("{0}: {1} ".format(nproc, series[nproc]))

  eff_table = gleaner.weak_efficiency( perfmap       = series, 
                                       size_per_node = 16777216,
                                       ppn           = 24,
                                       min_nodes     = 1 )
 
  if eff_table != None:
    print("Weak Scaling with 16777216 elements per node:")
    for nn, eff in eff_table:
      print("  {0} {1}".format(math.log(nn,2), eff))

  eff_table = gleaner.weak_efficiency( perfmap       = series,
                                       size_per_node = 2097152,
                                       ppn           = 24,
                                       min_nodes     = 1 )
  if eff_table != None:
    print("Weak Scaling with 2097152 elements per node:")
    for nn, eff in eff_table:
      print("  {0} {1}".format(math.log(nn,2), eff))

  strong_table = gleaner.strong_efficiency( perfmap    = series,
                                            total_size = 16777216,
                                            ppn        = 24,
                                            min_nodes  = 1 )
  if strong_table != None:
    print("Strong Scaling with 16777216 elements:")
    for nn, eff in strong_table:
      print("  {0} {1}".format(math.log(nn,2), eff))

  strong_table = gleaner.strong_efficiency( perfmap    = series,
                                            total_size = 134217728,
                                            ppn        = 24,
                                            min_nodes  = 1 )
  if strong_table != None:
    print("Strong Scaling with 134217728 elements:")
    for nn, eff in strong_table:
      print("  {0} {1}".format(math.log(nn,2), eff))

logging.info('Done checking')                          
logging.info('Finished')
