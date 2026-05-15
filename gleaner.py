#!/bin/python3
""" Helper tools to create plots from APES data.

This module provides some routines to import and
act on data from the APES tools.
Its purpose is to allow the easy creation of
small scripts that postprocess the produced data.

Copyright (c) 2015 Jigar Parekh <jigarparekh279@gmail.com>
Copyright (c) 2015-2016,2022 Kannan Masilamani <kannan.masilamani@dlr.de>
Copyright (c) 2016 Raphael Haupt <raphael.haupt@dlr.de>
Copyright (c) 2016, 2019, 2021-2022 Harald Klimach <harald.klimach@dlr.de>
Copyright (c) 2019 Peter Vitt <peter.vitt2@uni-siegen.de>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import logging
import re
from pathlib import Path

def first_word_of(string):
  ''' (string) -> string
      Get only the first word in a string and strip off all characters that are
      not considered to be part of a word.
  '''
  return re.match(r'\w+', string).group()


def untyped_colstring(columns):
  ''' (array of strings) -> string
      Small helping routine to create a list of names for SQL insertion.'''

  names = []
  for col in columns:
     names.append(first_word_of(col))
  return ', '.join(names)



def expand_table(sqlcon, tabname, columns, col_to_string=untyped_colstring):
  """ (sqlite3.Connection, string, array of strings,
       fun(array of strings)-> string)
      -> array of strings

      Expand a table (with name tabname) in sqlcon by the given columns.
      If the table does not yet exist, it will be created, if it exists, the
      columns are inserted, if they do not yet exist.
      Returned is an array of all the field names.
      Default is just joining all entries in a comma separated list.

      col_to_string is expected to provide a method to turn the list of
      column names into an SQL expression to add columns.
      This can be used to add data types to the columns.
  """

  column_titles = []
  for col in columns:
    column_titles.append(first_word_of(col))

  cols_string = col_to_string(column_titles)
  create_string = 'CREATE TABLE IF NOT EXISTS {0} ({1})'.format(tabname,
                                                                cols_string)
  sqlcon.execute(create_string)
  sqlcursor = sqlcon.execute('SELECT * FROM ' + tabname)
  colnames = list(map(lambda x: x[0], sqlcursor.description))
  newcols = [name for name in column_titles if name not in colnames]
  for nc in newcols:
    nc_qmarks = col_to_string(nc)
    alter_string = 'ALTER TABLE {0} ADD COLUMN {1}'.format(tabname, nc_qmarks)
    sqlcon.execute( alter_string )
  sqlcon.commit()

  sqlcursor = sqlcon.execute('SELECT * FROM {0}'.format(tabname))

  return list(map(lambda x: x[0], sqlcursor.description))


def get_columns(sqlcon, tabname, columns, as_nparray = False):
  ''' (sqlite3.Connections, string, array of strings or string, bool)
        -> array of arrays or array (or np.array)

      Get 'columns' from the table 'tabname' in the database connected by
      'sqlcons'.
      Returned is a list that contains each requested column as a list or if
      there is only one column, just the list for that column, or if
      'as_nparray' is True as numpy array.
  '''
  if as_nparray:
    import numpy as np
  sqlcursor = sqlcon.cursor()
  res = []
  if isinstance(columns, list):
    my_cols = columns
  else:
    my_cols = [columns]
  for col in my_cols:
    selquery = 'SELECT {0} FROM {1};'.format(col, tabname)
    sqlcursor.execute(selquery)
    if as_nparray:
      res.append(np.array([row[0] for row in sqlcursor.fetchall()]))
    else:
      res.append([row[0] for row in sqlcursor.fetchall()])

  if len(res) == 1:
    return res[0]
  else:
    return res


################################# DATABASE CREATION ############################
## Routine : Load data and append it
def file_to_db( sqlcon, filename, fieldnames, tabname,
                skiprows=0, col_to_string=untyped_colstring, delimiter=' ' ):

  '''
      ( string, array of strings, string, integer,
        fun(array of strings) -> string, string )
      Read data from file 'filename' and add it to the table 'tabname' in the
      database connected via 'sqlcon'.
      Use 'fieldnames' as headings for the columns.

      Optionally, skip first 'skiprows' rows, defaults to 0. Use this to skip
      header lines.

      'col_to_string' is a function that is used to convert column names into a
      string of names, potentially with type declarations for each field.
      Defaults to plain concatenation of all fieldnames separated by commata.

      'delimiter' is the characters to recognize as separators between columns.
      Defaults to spaces.
  '''

  import csv

  expand_table( sqlcon = sqlcon, tabname = tabname, columns = fieldnames,
                col_to_string = col_to_string )

  cur = sqlcon.cursor()
  with open(filename, 'r') as csvfile:
    datreader = csv.DictReader( csvfile, fieldnames=fieldnames,
                                delimiter=delimiter,
                                skipinitialspace=True )

    for i in range(skiprows):
      cols = next(datreader)

    for row in datreader:
      to_db = []
      col_titles = []
      for col in fieldnames:
        to_db.append(row[col])
        col_titles.append(first_word_of(col))
      cur.execute( 'INSERT INTO {0} ({1}) VALUES ({2});'.format(
                       tabname,
                       ', '.join(col_titles),
                       ', '.join('?'*len(col_titles)) ),
                   to_db )

  sqlcon.commit()
########################### END   database creation ############################


def add_to_db(fname, sqlcon, tabname, get_fieldnames, skiprows=1):
  ''' (string or array of strings, sqlite3.Connection, string, function)

      Read data from files given in 'fname' and collect them
      in the database connected in 'sqlcon' in the table 'tabname' (which is
      created if it does not exist yet).
      If the table already exists, its columns are extended to include all
      columns from the given file.

      'fname' might be a list of strings, or a single string. It is processed
      as a globbing expression and all files matching the globbing pattern will
      be added to the database.

      'get_fieldnames' has to be a function that takes a filename and extracts
      the column names for the table from it before attempting to get its
      data into the table.

      'skiprows' is the number of rows to skip in the read file.

  '''
  import glob
  if type(fname) in (list, tuple):
    for fin in fname:
      files = glob.glob(fin)
      for tfile in files:
        fieldnames = get_fieldnames(tfile)
        file_to_db( sqlcon, tfile, fieldnames, tabname, skiprows,
                    col_to_string = tracking_colstring )
  else:
    files = glob.glob(fname)
    for tfile in files:
      fieldnames = get_fieldnames(tfile)
      file_to_db( sqlcon, tfile, fieldnames, tabname, skiprows,
                  col_to_string = tracking_colstring )

def connect_and_add_to_db(fname, dbname, tabname, get_fieldnames, skiprows=1):
  ''' (string or array of strings, string, string) -> sqlite3.Connection
      Read timing data from timing.res files given in 'fname', and collect them
      in the database file 'dbname' in the table 'tabname' (which is created if
      it does not yet exist).
      If the table already exists, its columns are extended to include all
      columns from the given file.

      'fname' might be a list of strings, or a single string. It is processed
      as a globbing expression and all files matching the globbing pattern will
      be added to the database.

      'dbname' is the name of the database file to connect with. See
      sqlite3.connect for details.

      'get_fieldnames' has to be a function that takes a filename and extracts
      the column names for the table from it before attempting to get its
      data into the table.

      'skiprows' is the number of rows to skip in the read file.
  '''

  import sqlite3

  sqlcon = sqlite3.connect(dbname)
  add_to_db(fname, sqlcon, tabname, get_fieldnames, skiprows)
  return sqlcon


################### Methods to treat timing.res data. ##########################
def timing_colstring(columns):
  """ (array of strings) -> string

      Create a string to represent <columns> names, suitable to be used in SQL
      queries.
      This automatically adds the data type as expected for columns from the
      timing.res created by the APES tools.

      Example:
      >>> timing_colstring(['nProcs', 'simLoop'])
      'nProcs INTEGER, simLoop REAL'
  """
  columntypes = {
      'nProcs'      : 'INTEGER',
      'threads'     : 'INTEGER',
      'DomSize'     : 'INTEGER',
      'Dofs'        : 'INTEGER',
      'DofPE'       : 'INTEGER',
      'DofPEPV'     : 'INTEGER',
      'nVars'       : 'INTEGER',
      'KEUPS'       : 'REAL',
      'KDUPS'       : 'REAL',
      'MLUPs'       : 'REAL',
      'maxIter'     : 'INTEGER',
      'ATELES'      : 'REAL',
      'initialize'  : 'REAL',
      'simLoop'     : 'REAL',
      'commState'   : 'REAL',
      'Output'      : 'REAL',
      'preprocKern' : 'REAL',
      'projToFace'  : 'REAL',
      'setBnd'      : 'REAL',
      'invMassMat'  : 'REAL',
      'numFlux'     : 'REAL',
      'physFlux'    : 'REAL',
      'projTestFun' : 'REAL',
      'invMassT'    : 'REAL',
      'localProj'   : 'REAL',
      'MemRSS'      : 'INTEGER',
      'MemHWM'      : 'INTEGER'
  }

  typedColumns = []
  for col in columns:
    colname = first_word_of(col)
    if col in columntypes:
      typedColumns.append(colname + ' ' + columntypes[col])
    else:
      typedColumns.append(colname)

  return ', '.join(typedColumns)


def get_timing_header(filename):
  """ (string) -> array of strings
      Get the column names from the header in a timing.res file.
  """

  import csv

  # Find and store the file header line for column names
  colhead = []
  with open(filename, 'r') as csvfile:
    timereader = csv.reader( csvfile, delimiter = ' ',
                             skipinitialspace = True  )
    cols = next(timereader)

  # Delete the comment column from the header line.
  if cols[0] == '#':
    del cols[0]

  colhead = []
  for cname in cols:
    colhead += cname.strip('|').split('|')

  dups = {}
  unified = []
  for cname in colhead:
    if cname not in unified:
      unified.append(cname)

    else:
      if cname not in dups:
        dups[cname] = 1
      dups[cname] = dups[cname]+1
      unified.append("{0}_{1:d}".format(cname, dups[cname]))

  return unified


def load_timing_dataframe(filename):
  """ (string or pathlib.Path) -> pandas.DataFrame
      Read timing data into a pandas DataFrame using the extracted header.
  """

  import pandas as pd

  filename = Path(filename)
  header_names = get_timing_header(filename)

  df = pd.read_csv(
      filename,
      sep=r'\s+',
      engine='python',
      comment='#',
      header=None
  )

  if df.shape[1] != len(header_names):
    raise ValueError(
        'Header/data column mismatch in {0}: {1} headers, {2} data columns'
        .format(filename, len(header_names), df.shape[1])
    )

  df.columns = header_names
  return df


def timing_to_db(fname, dbname, tabname):
  ''' (string or array of strings, string, string) -> sqlite3.Connection
      Read timing data from timing.res files given in 'fname', and collect them
      in the database file 'dbname' in the table 'tabname' (which is created if
      it does not yet exist).
      If the table already exists, its columns are extended to include all
      columns from the given file.

      'fname' might be a list of strings, or a single string. It is processed
      as a globbing expression and all files matching the globbing pattern will
      be added to the database.

      'dbname' is the name of the database file to connect with. See
      sqlite3.connect for details.
  '''

  return connect_and_add_to_db(fname, dbname, tabname, get_timing_header, skiprows=1)


def add_timing_to_db(fname, sqlcon, tabname):
  ''' (string or array of strings, sqlite3.Connection, string)
      Read timing data from timing.res files given in 'fname', and collect them
      in the database given by sqlcon in the table 'tabname' (which is created if
      it does not yet exist).
      If the table already exists, its columns are extended to include all
      columns from the given file.

      'fname' might be a list of strings, or a single string. It is processed
      as a globbing expression and all files matching the globbing pattern will
      be added to the database.

      'sqlcon' is the Connector of an existing database.
  '''

  add_to_db(fname, sqlcon, tabname, get_timing_header, skiprows=1)

################################ End timing.res ################################


################### Methods to treat ascii tracking data. ######################
def tracking_colstring(columns):
  """ (array of strings) -> string

      Create a string to represent <columns> names, suitable to be used in SQL
      queries.
      This automatically adds the data type as expected for columns from the
      tracking ASCII data created by the APES tools (all reals).

      Example:
      >>> tracking_colstring(['coordX', 'density'])
      'coordX REAL, density REAL'
  """

  typedColumns = []
  for col in columns:
    colname = first_word_of(col)
    typedColumns.append('{0} REAL'.format(colname))

  return ', '.join(typedColumns)


def get_tracking_header(filename):
  """ (string) -> array of strings
      Get the column names from the header in an ASCII tracking file.
  """

  import csv

  # Find and store the file header line for column names
  colhead = []
  with open(filename, 'r') as csvfile:
    timereader = csv.reader( csvfile, delimiter = ' ',
                             skipinitialspace = True  )
    colhead = next(timereader)
    colhead = next(timereader)

  # Delete the comment column from the header line.
  if colhead[0] == '#':
    del colhead[0]

  return colhead

def tracking_append(fname, sqlcon, tabname):
  ''' (string or array of strings, sqlite3.Connection, string)

      Read tracking data from files given in 'fname' and collect them
      in the database connected in 'sqlcon' in the table 'tabname' (which is
      created if it does not exist yet).
      If the table already exists, its columns are extended to include all
      columns from the given file.

      'fname' might be a list of strings, or a single string. It is processed
      as a globbing expression and all files matching the globbing pattern will
      be added to the database.

  '''

  add_to_db(fname, sqlcon, tabname, get_tracking_header, skiprows=2)

def tracking_to_db(fname, dbname, tabname):
  ''' (string or array of strings, string) -> sqlite3.Connection
      Read tracking data from files given in 'fname', and collect them
      in the database file 'dbname' in the table 'tabname' (which is created if
      it does not yet exist).
      If the table already exists, its columns are extended to include all
      columns from the given file.

      'fname' might be a list of strings, or a single string. It is processed
      as a globbing expression and all files matching the globbing pattern will
      be added to the database.

      'dbname' is the name of the database file to connect with. See
      sqlite3.connect for details.
      A resulting connector to the database will be returned.
  '''

  return connect_and_add_to_db(fname, dbname, tabname, get_tracking_header, skiprows=2)

################################ End tracking ##################################


################### Methods to treat csv paraview data. ########################
def get_paraview_header(filename):
  """ (string) -> array of strings
      Get the column names from the header in a CSV file from paraview.
  """
  import csv

  # Find and store the file header line for column names
  colhead = []
  with open(filename, 'r') as csvfile:
    timereader = csv.reader( csvfile, delimiter = ',',
                             skipinitialspace = True  )
    cols = next(timereader)

  # Delete the comment column from the header line.
  if cols[0] == '#':
    del cols[0]

  # replace : used for vector variable name with _
  colhead = []
  for cname in cols:
    colhead.append(cname.replace(':','_'))

  return colhead

def paraview_append(fname, sqlcon, tabname):
  ''' (string or array of strings, sqlite3.Connection, string)

      Read paraview csv data from files given in 'fname' and collect them
      in the database connected in 'sqlcon' in the table 'tabname' (which is
      created if it does not exist yet).
      If the table already exists, its columns are extended to include all
      columns from the given file.

      'fname' might be a list of strings, or a single string. It is processed
      as a globbing expression and all files matching the globbing pattern will
      be added to the database.

  '''

  add_to_db(fname, sqlcon, tabname, get_paraview_header, skiprows=2)

def paraview_to_db(fname, dbname, tabname):
  ''' (string or array of strings, string) -> sqlite3.Connection
      Read paraview csv data from files given in 'fname', and collect them
      in the database file 'dbname' in the table 'tabname' (which is created if
      it does not yet exist).
      If the table already exists, its columns are extended to include all
      columns from the given file.

      'fname' might be a list of strings, or a single string. It is processed
      as a globbing expression and all files matching the globbing pattern will
      be added to the database.

      'dbname' is the name of the database file to connect with. See
      sqlite3.connect for details.
      A resulting connector to the database will be returned.
  '''

  return connect_and_add_to_db(fname, dbname, tabname, get_paraview_header, skiprows=2)

################################ End paraview ##################################


################################ DATA ANALYSIS #################################
def drop_existing(cur, tabname):
  ''' (sqlcursor, string)
      Drop a table in the database, if it already exists.
  '''
  cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='" + tabname + "'")
  # if the count is 1, then table exists
  if cur.fetchone()[0] == 1:
    print('Warning: Table ' + tabname + ' already exists. Dropping table and recreating')
    cur.execute('DROP TABLE ' + tabname)

def fill_reduced_table(sqlcon, red_tabname, reduced_data, x_key):
  ''' (sqlite3.Connection, string, dict of arrays, string)
      Fill reduced_data into the table red_tabname of the database connected in
      sqlcon.
      x_key provides the column to take the reduced data about.
      If the table already exists, it is dropped and recreated.
  '''
  cur = sqlcon.cursor()

  drop_existing(cur, red_tabname)

  expand_table( sqlcon, tabname = red_tabname, columns = reduced_data.keys(),
                        col_to_string = tracking_colstring )

  for row in range(len(reduced_data[x_key])):
    to_db = []
    col_titles = []
    for col in reduced_data.keys():
      to_db.append(reduced_data[col][row])
      col_titles.append(first_word_of(col))
    cur.execute( 'INSERT INTO {0} ({1}) VALUES ({2});'.format(
                     red_tabname,
                     ', '.join(col_titles),
                     ', '.join('?'*len(col_titles)) ),
                 to_db )
  sqlcon.commit()

def spatial_reduction_in_db(sqlcon, tabname, columns, reduce_coord_column):
  ''' (sqlite3.Connection, string, array of strings, string)

      Reduce columns with respect to reduce_coord_column

      Read data with 'columns' from 'sqlcon' under the table 'tabname' and
      reduce those columns along 'reduction_coord'. Reduced columns are written
      into 'sqlcon' under the table 'tabname'_red.
  '''
  import numpy as np
  coord_val_red = get_columns(sqlcon, tabname, columns=[reduce_coord_column])
  col_val_red = dict()

  for col in columns:
    val = get_columns(sqlcon, tabname, columns=[col])
    val_dict = dict()
    for ii in range(len(coord_val_red)):
      key = str(coord_val_red[ii])
      if key in val_dict:
        val_dict[key].append(val[ii])
      else:
        val_dict[key] = [val[ii]]

    col_val_red[col] = np.array([])
    for key in val_dict:
       col_val_red[col] = np.append(col_val_red[col],
                                    np.average(np.array(val_dict[key])))

  fill_reduced_table(sqlcon, tabname + "_red", col_val_red, reduce_coord_column)


def spatial_reduction_3d_to_2d_in_db(sqlcon, tabname, columns, reduce_coord_column):
  """ (sqlite3.Connection, string, array of strings, string)

      Reduce columns with respect to reduce_coord_column.
      reduce_coord_column should contain any two column headers from ['coordX','coordY', 'coordZ']
      e.g ['coordX','coordZ']

      Read data with 'columns' from 'sqlcon' under the table 'tabname' and
      reduce those columns along 'reduce_coord_column'. Reduced columns are written
      into 'sqlcon' under the table 'tabname'_red.
  """
  import numpy as np
  coord_val_red_1, coord_val_red_2 = get_columns(sqlcon, tabname, columns=reduce_coord_column)
  col_val_red = dict()

  for col in columns:
    val = get_columns(sqlcon, tabname, columns=[col])
    val_dict = dict()
    for ii in range(len(coord_val_red_1)):
      # key variable stores unique co-ordinate values (a,b) from coord_val_red_1 and coord_val_red_1
      key = f"{coord_val_red_1[ii]}, {coord_val_red_2[ii]}"
      if key in val_dict:
        val_dict[key].append(val[ii])
      else:
        val_dict[key] = [val[ii]]
    # print(val_dict)
    col_val_red[col] = np.array([])
    for key in val_dict:
      col_val_red[col] = np.append(col_val_red[col],
                                   np.average(np.array(val_dict[key])))
  fill_reduced_table(sqlcon, tabname + "_red", col_val_red, reduce_coord_column[0])


def radial_reduction_in_db(sqlcon, tabname, columns, coord_column,
                           geometry_pos):
  ''' (sqlite3.Connection, string, array of strings, array of strings,
       list of floats)
      Average columns along the radial direction (around the z axis) to
      plot data over angle.

      Read data with 'columns' from 'sqlcon' under the table 'tabname' and
      reduce those columns along theta computed from
      180-math.atan2(coordY[ii][0] - geometry_pos[1],
                     coordX[ii][0] - geometry_pos[0])*180/math.pi
      Reduced columns and theta are written into 'sqlcon' under the table
      'tabname'_red.
  '''
  import numpy as np
  import math
  [coordX, coordY] = get_columns(sqlcon, tabname, columns=coord_column)
  theta_red = np.array([])
  col_val_red = dict()
  for col in columns:
    if col not in coord_column:
      val = get_columns(sqlcon, tabname, columns=[col])
      val_dict = dict()
      for ii in range(len(coordX)):
        key = 180 - math.atan2(coordY[ii] - geometry_pos[1],
                               coordX[ii] - geometry_pos[0]) * 180 / math.pi
        if key in val_dict:
          val_dict[key].append(val[ii])
        else:
          val_dict[key] = [val[ii]]
          if col == columns[0]:
            theta_red = np.append(theta_red, key)

      col_val_red[col] = np.array([])
      for key in val_dict:
         col_val_red[col] = np.append(col_val_red[col],
                                      np.average(np.array(val_dict[key])))

  col_val_red['theta'] = theta_red
  fill_reduced_table(sqlcon, tabname + '_red', col_val_red, 'theta')


## Routine : Find distinct sets from database
def distinct_sets(sqlcon, tabname, signature, constraint=''):

  """ (sqlite3.Connector, string, array of strings, string) -> array of dicts

      Find distinct entries in the database connected by <sqlcon>, matching the
      given <signature> under the <constraint> in table <tabname>.
      The string in <constraint> has to be a valid SQL WHERE clause or empty.
      As a result all unique combinations of the <signature> from the database
      are returned in a dictionary with the <signature> strings as keys.
  """

  sig = list(signature)
  col = sig.pop()

  if constraint == '':
    conjunc = ' WHERE '
  else:
    conjunc = ' AND '

  selquery = 'SELECT DISTINCT ' + col + ' FROM ' + tabname + constraint

  res = []
  if len(sig) == 0:
    for val in sqlcon.execute(selquery):
      res.append({col: val[0]})
  else:
    precons = constraint + conjunc + col + "='"
    for val in sqlcon.execute(selquery):
      childconstraint = "{0}{1}'".format(precons, val[0])
      childs = distinct_sets(sqlcon, tabname, sig, constraint = childconstraint)

      for child in childs:
        child[col] = val[0]
        res.append(child)

  return res


## Routine : Creates x-y data in accordance with keys of <selections> and the
##           type of <reduction> method
def collected_xy_series(sqlcon, tabname, selections, x, y, reduction="median"):

  """ (sqlite3.Connector, string, list of dicts, string, list of strings,
       string) -> dict of dicts, namedtuple

      Create xy data series from the database in <sqlcon> for all <selections>,
      where <y> are the columns to pick and to plot over <x>. The <reduction>
      is used to reduce possibly duplicate entries to a single value.
      <x> has to be found in the keys of <selections>.
      The resulting dicts contain the key-value pairs from selections, except
      the <x>, and for each of these an array of data with (x, y) tuples,
      sorted by x.
      As a second result the namedtuple, that can be used to identify each point
      is returned.
  """

  from collections import namedtuple
  from bisect import insort

  res = {}
  id_keys = [key for key in selections[0].keys() if key != x]
  ID_tuple = namedtuple('ID_tuple', id_keys)
  ydat = data_for_sets(sqlcon, tabname, selections, y, reduction)
  for i in range(len(ydat)):
    sel = selections[i]
    xdat = float(sel[x])
    id_vals = [value for key, value in sel.items() if key != x]
    sel_id = ID_tuple._make(id_vals)
    if sel_id not in res:
      res[sel_id] = []
    insort(res[sel_id], (xdat, ydat[i]))

  return (res, ID_tuple)


##Routine : Obtaining 'ydat'
def data_for_sets(sqlcon, tabname, selections, cols, reduction="median"):
  """ (sqlite3.Connector, string, list of dicts, list of strings, string) -> list of lists

      Look up the reduced data in <cols> from the database in "sqlcon" for all
      <selections> using the <reduction> operation out of table <tabname>.
  """

  res = []
  for sel in selections:
    res.append(reduced_set(sqlcon, tabname, sel, cols, reduction))

  return(res)


##Routine : Obtaining a single value according to the <reduction> type
def reduced_set(sqlcon, tabname, selection, cols, reduction="median"):
  """ (sqlite3.Connector, string, dict of strings, list of strings, string) -> list of numbers

      For a set of numbers identified by <selection> in the database connected
      with <sqlcon> return reduced numerical values for data in columns <col>.
      The <reduction> states, how to obtain a single value for all the matching
      entries of <selection> in table <tabname>.
  """

  res = []
  for col in cols:
    vals = number_set(sqlcon, tabname, selection, col)
    if reduction == 'median':
      res.append(median(vals))
    elif reduction == 'min':
      res.append(vals[0])
    elif reduction == 'max':
      res.append(vals[-1])
    elif reduction == 'mean':
      res.append(float(sum(vals))/float(len(vals)))
  return(res)


## Routine : Sorting of entries in <col> from database
def number_set(sqlcon, tabname, selection, col):
  """ (sqlite3.Connector, string, dict of strings, string) -> list of numbers

      Get values out of the database connected by <sqlcon>, under the constraint
      given by <selection> in table <tabname>.
      The result will be the numerically sorted values from <col> in the
      database and is supposed to be numbers.
  """

  constraints = []
  for (name, val) in selection.items():
    constraints.append("{0}='{1}'".format(name, val))
  selquery = 'SELECT ' + col + ' FROM ' + tabname + ' WHERE ' + ' AND '.join(constraints)
  cur = sqlcon.cursor()
  cur.execute(selquery)
  res_str = cur.fetchall()
  res = []
  for strval in res_str:
    res.append(float(strval[0]))
  return sorted(res)


## Routine : Find median of a sortedlist
def median(sortedlist):
  """ (list of numbers) -> float

      Returns the median of a <sortedlist>. If there is an even number of
      entries in <sortedlist>, the average of the middle two values is
      returned.
  """

  length = len(sortedlist)
  irem = 1 - length % 2
  halved = length / 2
  return(0.5 * (sortedlist[int(halved)] + sortedlist[int(halved-irem)]))


##Routine : For printing the series gathered from <data> and identified by <sig>
def dump_xy_series(data, sig, x, y, gnuplot = False, f = sys.stdout):
  """ (dict, ID_tuple, string, array of strings, bool, file object)

      Print a series gathered from <data> and identified by <sig> to the
      file <f> or to the screen, if no file is provided.
      <x> is used as a heading for the first column, while <y> provides the
      names for the remaining columns.
      If <gnuplot> is set to True, the header will be prepended by a '#' to
      allow easier processing in gnuplot.
  """

  # Comment line of headings for gnuplot.
  if gnuplot:
    f.write('# ')

  f.write(x + ' ' + ' '.join(y) + '\n')
  dump_xy_series_data(data, sig, f)


##Routine : For printing the series gathered from <data>
def dump_xy_series_data(data, sig, f = sys.stdout):
  """ (dict, ID_tuple, file object)

      Print a series gathered from <data> and identified by <sig> to the
      file <f> or to the screen, if no file is provided.
  """

  for line in data[sig]:
    f.write(str(line[0]) + ' ' + ' '.join([str(y) for y in line[1]])+'\n')


##Routine : Find the y values found for <x> in the given <series>
def xy_series_value_at(series, x):
  """ (array of tuples, float) -> array of floats

      Return the y values found for <x> in the given <series>, or
      None, if <x> is outside the range of the <series>.
      Values between actual existing data points are obtained by
      linear interpolation.
  """

  from bisect import bisect

  xvals = [xe for xe,ye in series]
  if x >= xvals[0] and x <= xvals[-1]:
    if len(xvals) == 1:
      return (series[0][1])
    else:
      pos_right = min(max(bisect(xvals, x), 1), len(xvals)-1)
      pos_left = pos_right - 1
      x_left = xvals[pos_left]
      xrange = float(xvals[pos_right] - x_left)
      y_left = series[pos_left][1]
      y_right = series[pos_right][1]
      res = []
      for i in range(len(y_left)):
        yrange = float(y_right[i] - y_left[i])
        res.append(y_left[i] + (yrange/xrange)*(x - x_left))
      return(res)


############################### SCALING PLOTS ##################################

def perfmap_series(sqlcon, tabname, signature, xcol, ycol, reduction = 'median',
                   constraint = '', nProcsCol = 'nProcs'):
  """ (sqlite3.Connector, string, array of strings, string, string, string,
       string, string) -> dict of arrays

      Get all performance map series from the database in <sqlcon>.
      Individual runs are identified by <signature> and the x-axis is
      given by the data in <xcol>, usually this should be "DomSize".
      Each series is done for a specific number of processes, where the
      number of processes are identified by the <nProcsCol>, usually "nProcs".
      The data to track over x is given by <ycol> and is typically a
      performance measure like KDUPS or MLUPS.
      If there are multiple entries for the same run, <reduction> is used to
      obtain a single value out of them (defaults to the median).
      Data to select from the database can be restricted by <constraint>.

      The resulting data is identified by the nProcs and further identifying
      parts from the signature, and an array of x,y tuples:
      res = {namedtuple: {nProcs: [(x,y)]}}
  """

  logging.info('In Routine -> perfmap_series ...')
  from collections import namedtuple

  if len(signature) == 0:
    print('ERROR: In perfmap_series')
    print("       List signature is empty.")
    logging.error('In perfmap_series : List signature is empty ')

  if len(xcol) == 0:
    print('ERROR: In perfmap_series')
    print("       List xcol is empty.")
    logging.error('In perfmap_series : List xcol is empty ')

  if len(ycol) == 0:
    print('ERROR: In perfmap_series')
    print("       List ycol is empty.")
    logging.error('In perfmap_series : List ycol is empty ')

  else:
    runs = distinct_sets(sqlcon, tabname, signature)
    perf, FullID = collected_xy_series(sqlcon, tabname, runs, xcol,
                                                     [ycol], reduction)
    id_keys = [key for key in FullID._fields if key != nProcsCol]
    ID_tuple = namedtuple('ID_tuple', id_keys)

    res = {}
    for fullsig, series in perf.items():
      id_vals = [fullsig._asdict()[fid] for fid in id_keys]
      new_id = ID_tuple._make(id_vals)
      res.setdefault(new_id, {})[int(fullsig.nProcs)] = series
    logging.info('Returning the tuples: res = {namedtuple: {nProcs: [(x,y)]}}')
    return(res, ID_tuple)


def weak_scaling(perfmap, size_per_node, ppn=1, normalize=False,
                 min_nodes=None, max_nodes=None, interpolation=True):
  """ (dict, float, int, bool, int, int) -> list of tuples

      Create a weak-scaling plot out of the data provided in <perfmap>, which
      has to be one entry from a dict created by perfmap_series.
      That is, <perfmap> has to look like: {nProcs: [(x,y)]}, where x defines
      the problem size and y the performance at that point.
      <size_per_node> states, which x to pick out of the various series.
      With <ppn> (processes per node) you can control what the basic processing
      unit should be. All measures will be done for nProcs/ppn.
      If <normalize> is set to True, the y values will be divided by the
      number of processing units (nProcs/ppn).
      If you want to limit the range of nodes to use, you can select the
      minimal number of nodes to consider with <min_nodes>, and the maximal
      number of nodes by <max_nodes>.
      If <interpolation> set to False, no linear interplation for missing values
      will be done, default is True.
  """
  from bisect import bisect

  nProcs = sorted(perfmap.keys())
  if min_nodes:
    min_procs = max(min_nodes*ppn, nProcs[0])
  else:
    min_procs = nProcs[0]

  if max_nodes:
    max_procs = min(max_nodes*ppn, nProcs[-1])
  else:
    max_procs = nProcs[-1]

  res = []
  for p in nProcs:
    if p >= min_procs and p <= max_procs:
      nNodes = p/float(ppn)
      total_size = size_per_node * nNodes
      if interpolation:
       y = xy_series_value_at(series = perfmap[p], x = total_size)
       if y:
        if normalize:
         val = y[0]/nNodes
        else:
         val = y[0]
        res.append((nNodes, val))
      else:
       xvals = [xe for xe,ye in perfmap[p]]
       if total_size in (xvals):
        x_pos=bisect(xvals,total_size)
        y = perfmap[p][x_pos-1][1]
        if normalize:
         val = y[0]/nNodes
        else:
         val = y[0]
        res.append((nNodes,val))
  return(res)


def weak_efficiency(perfmap, size_per_node, ppn=1, ref_perf=None,
                    min_nodes=None, max_nodes=None,interpolation=True):
  """ (dict, float, int, float, int, int) -> list of tuples

      Create a weak scaling series with the efficiency over number of nodes.
      The data in <perfmap> has to an entry from a dict created by
      perfmap_series with this form: {nProcs: [(x,y)]}, where x defines
      the problem size and y the performance at that point.
      Here y has to be a performance measure (usually proportional to the
      inverse of the time)!
      With <size_per_node>, the point on the x axis is selected, at which
      the weak scaling is to be extracted.
      The basic processing unit, that is to be used can be set by <ppn>,
      specifying the number of processes per node.
      Per default the performance per node for the smallest process count is
      chosen as reference. This can be overwritten by <ref_perf>. If this is
      present it will be used instead of the performance on the smallest
      node count.
      To restrict the range of the scaling <min_nodes> and <max_nodes> might
      be provided.
      If <interpolation> set to False, no linear interplation for missing values
      will be done in weak_scaling, default is true.
  """

  print("INFO: Extract weak efficiency for size_per_node ", size_per_node)

  scalings = weak_scaling(perfmap, size_per_node, ppn, normalize=True,
                          min_nodes=min_nodes, max_nodes=max_nodes, interpolation=interpolation)

  res = None
  if len(scalings) == 0:
    print('ERROR: In Weak efficicency')
    print('       No data found for size_per_node: ', size_per_node)
  else:
    if not ref_perf:
      ref_perf = scalings[0][1]

    res = [(nNodes, y/ref_perf) for nNodes, y in scalings]

  return res


def strong_scaling(perfmap, total_size, ppn=1, normalize=False,
                 min_nodes=None, max_nodes=None,interpolation=True):
  """ (dict, float, int, bool, int, int) -> list of tuples

      Create a strong-scaling plot out of the data provided in <perfmap>, which
      has to be one entry from a dict created by perfmap_series.
      That is, <perfmap> has to look like: {nProcs: [(x,y)]}, where x defines
      the problem size and y the performance at that point.
      <total_size> states, which x to pick out of the various series.
      With <ppn> (processes per node) you can control what the basic processing
      unit should be. All measures will be done for nProcs/ppn.
      If <normalize> is set to True, the y values will be divided by the
      number of processing units (nProcs/ppn).
      If you want to limit the range of nodes to use, you can select the
      minimal number of nodes to consider with <min_nodes>, and the maximal
      number of nodes by <max_nodes>.
      If <interpolation> set to False, no linear interplation for missing values
      will be done, default is true.
  """

  from bisect import bisect

  nProcs = sorted(perfmap.keys())
  if min_nodes:
    min_procs = max(min_nodes*ppn, nProcs[0])
  else:
    min_procs = nProcs[0]

  if max_nodes:
    max_procs = min(max_nodes*ppn, nProcs[-1])
  else:
    max_procs = nProcs[-1]

  res = []
  for p in nProcs:
    if p >= min_procs and p <= max_procs:
      nNodes = p/float(ppn)
      if interpolation:
       y = xy_series_value_at(series = perfmap[p], x = total_size)
       if y:
         if normalize:
           val = y[0]/nNodes
         else:
           val = y[0]
         res.append((nNodes, val))
      else:
       xvals = [xe for xe,ye in perfmap[p]]
       if total_size in (xvals):
        x_pos=bisect(xvals,total_size)
        y = perfmap[p][x_pos-1][1]
        if normalize:
         val = y[0]/nNodes
        else:
         val = y[0]
        res.append((nNodes,val))
  return(res)


def strong_efficiency(perfmap, total_size, ppn=1, ref_perf=None,
                      min_nodes=None, max_nodes=None, interpolation=True):
  """ (dict, float, int, float, int, int) -> list of tuples

      Create a strong scaling series with the efficiency over number of nodes.
      The data in <perfmap> has to an entry from a dict created by
      perfmap_series with this form: {nProcs: [(x,y)]}, where x defines
      the problem size and y the performance at that point.
      Here y has to be a performance measure (usually proportional to the
      inverse of the time)!
      With <size_per_node>, the point on the x axis is selected, at which
      the strong scaling is to be extracted.
      The basic processing unit, that is to be used can be set by <ppn>,
      specifying the number of processes per node.
      Per default the performance per node for the smallest process count is
      chosen as reference. This can be overwritten by <ref_perf>. If this is
      present it will be used instead of the performance on the smallest
      node count.
      To restrict the range of the scaling <min_nodes> and <max_nodes> might
      be provided.
      If <interpolation> set to False, no linear interplation for missing values
      will be done in strong_scaling, default is True.
  """

  print("INFO: Extract strong efficiency for total size ", total_size)

  scalings = strong_scaling(perfmap, total_size, ppn, normalize=True,
                          min_nodes=min_nodes, max_nodes=max_nodes,interpolation=interpolation)

  res = None
  if len(scalings) == 0:
    print('ERROR: In Strong efficicency')
    print("       No data found for total_size: ", total_size)
  else:
    if not ref_perf:
      ref_perf = scalings[0][1]

    res = [(nNodes, y/ref_perf) for nNodes, y in scalings]

  return res


# The upcoming functions were developed by Achuthan Rajendran,
# Master student, TU Dresden, as a part of the Master Thesis
######################## Tracking muliple ASCII files to database ######################################################
def tracking_multiple_data_to_db(dbname, input_files):
  """ (string, string or list of strings)
      input_files are ASCII files containing instantaneous velocities which are tracked to the
      database: dbname under each table for each ASCII file.

      Returns sqlcon (a sqlite3.Connection) to the database: dbname and all_tab_names
      consisting of all table names of the database
  """
  from pathlib import Path
  import sqlite3
  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)
  import os

  all_tab_names = []
  sqlcon = sqlite3.connect(dbname)
  for file, i in zip(input_files, range(len(input_files))):
    indv_file = Path(file).stem
    indv_file = indv_file.replace('_p00000', '')
    all_tab_names.append(indv_file)
    try:
      if os.path.isfile(dbname):
        cur = sqlcon.cursor()
        drop_existing(cur, tabname=indv_file)
        logger.info(f'Adding data to the database: {dbname}')
        sqlcon = tracking_to_db(fname=file, dbname=dbname, tabname=indv_file)

    except Exception as e:
      logger.error(f"Error processing file {file}: {str(e)}")
    ## -------------------------------------------------------------------------- ##

  return sqlcon, all_tab_names
######################################################################################################################


########################## Statistical quantities calculation ###############################################
def find_index_of_value_or_nearest(data, value, tolerance=1e-9):
  """ (list, int or float)
      Finds the index of a specific value in a list.
      If the value is not found, it returns the index of the nearest value.
  """

  # Check if the exact value is in the list (within a small tolerance)
  exact_matches = [i for i, x in enumerate(data) if abs(x - value) <= tolerance]

  if exact_matches:
    exact_index = exact_matches[0]
    print(f"\nExact value {value} found at index: {exact_index}")
    return exact_index, value
  else:
    # If not exact match, find the nearest value
    differences = [abs(x - value) for x in data]
    nearest_index = differences.index(min(differences))
    nearest_value = data[nearest_index]
    print(f"\nExact value {value} not found.")
    print(f"Nearest value found is {nearest_value} at index: {nearest_index}")
    return nearest_index, nearest_value


def statistical_quantities_calc(sqlcon, all_tab_names):
  """ (sqlite3.connections, list of strings)
      Get column values from the tables 'all_tab_names' in the database connected by
     'sqlcon'.

      Calculates statistical quantities for entire columns or just a sample and stores all the values
      to database

      Before using this function make sure to use the function: tracking_multiple_data_to_db(dbname, input_files)
      if there is no instantaneous velocity data in a database
  """
  import math
  for table in all_tab_names:
    header_names = ['time', 'velocity_phy_01', 'velocity_phy_02', 'velocity_phy_03']
    # get_columns, a function inside gleaner which extracts values of each column from sql database
    t, u, v, w = get_columns(sqlcon, tabname=table,
                                     columns=header_names)
    print(f"\nCalculate statistical quantities for {table}")
    while True:

      print("Choose your choice for calculating statistical quantities"
            "\nChoice 1: Calculate statistical quantities for the entire columns of data"
            "\nChoice 2: Calculate statistical quantities for a sample (a portion of columns) by specifying "
            "start and end time")

      choice = int(input("\nSelect your choice (Type 1 or 2): "))
      match choice:
        case 1:
          print()
          total_rows = len(u)
          print("Entire columns of data are taken to calculate statistical quantities")
          break
        case 2:
          try:
            start_value = float(input("\nEnter the start time: "))
            start_index, value_1 = find_index_of_value_or_nearest(t, start_value)
            end_value = float(input("\nEnter the end time: "))
            end_index, value_2 = find_index_of_value_or_nearest(t, end_value)

          except ValueError:
            print("Invalid input. Please try again.")


          print(f'A sample of velocity data are taken from the {value_1:.4f} to {value_2:.4f} '
                f'\nto calculate statistical quantities')
          # Initialize variables

          u = u[start_index:end_index + 1]
          v = v[start_index:end_index + 1]
          w = w[start_index:end_index + 1]
          total_rows = len(u)
          break

        case _:
          print("\nInvalid number. Try again")

    inst_velocity_U = 0
    inst_velocity_V = 0
    inst_velocity_W = 0

    U_prime_sum_of_square = 0
    V_prime_sum_of_square = 0
    W_prime_sum_of_square = 0

    U_prime_sum_of_cubes = 0
    V_prime_sum_of_cubes = 0
    W_prime_sum_of_cubes = 0

    U_prime_sum_of_quads = 0
    V_prime_sum_of_quads = 0
    W_prime_sum_of_quads = 0

    Reynolds_shear_stress_uv = 0
    Reynolds_shear_stress_uw = 0
    Reynolds_shear_stress_vw = 0

    # The formula for each statistical quantity is available in the paper in Theoretical foundations section:
    # Agarwal, M., Deshpande, V., Katoshevski, D. et al. A novel Python module for statistical analysis of
    # turbulence (P-SAT) in geophysical flows. Sci Rep 11, 3998 (2021). https://doi.org/10.1038/s41598-021-83212-1
    # Calculation of mean velocities
    for i in range(total_rows):
        inst_velocity_U += u[i]
        inst_velocity_V += v[i]
        inst_velocity_W += w[i]

    average_velocity_U = inst_velocity_U / total_rows
    average_velocity_V = inst_velocity_V / total_rows
    average_velocity_W = inst_velocity_W / total_rows

    # Calculation of fluctuating velocities
    for i in range(total_rows):
        #Fluctuating_velocity = Instantaneous_velocity - Mean_velocity
        #U_prime, V_prime and W_prime are the fluctuating component of velocities
        U_prime = u[i] - average_velocity_U
        U_prime_sum_of_square += U_prime * U_prime
        U_prime_sum_of_cubes += U_prime * U_prime * U_prime
        U_prime_sum_of_quads += pow(U_prime, 4)

        V_prime = v[i] - average_velocity_V
        V_prime_sum_of_square += V_prime * V_prime
        V_prime_sum_of_cubes += V_prime * V_prime * V_prime
        V_prime_sum_of_quads += pow(V_prime, 4)

        W_prime = w[i] - average_velocity_W
        W_prime_sum_of_square += W_prime * W_prime
        W_prime_sum_of_cubes += W_prime * W_prime * W_prime
        W_prime_sum_of_quads += pow(W_prime, 4)

        Reynolds_shear_stress_uv += U_prime * V_prime
        Reynolds_shear_stress_uw += U_prime * W_prime
        Reynolds_shear_stress_vw += V_prime * W_prime

    #-------- End of the for loop for calculation of U_prime, V_prime and W_prime for each time interval ----------#

    # Calculation of Variances
    U_variance = U_prime_sum_of_square / total_rows
    V_variance = V_prime_sum_of_square / total_rows
    W_variance = W_prime_sum_of_square / total_rows

    # Calculation of Standard deviation
    U_stdev = math.sqrt(U_variance)
    V_stdev = math.sqrt(V_variance)
    W_stdev = math.sqrt(W_variance)

    # Calculation of Skewness
    U_skew = pow(U_variance, (-3 / 2)) * (U_prime_sum_of_cubes / total_rows)
    V_skew = pow(V_variance, (-3 / 2)) * (V_prime_sum_of_cubes / total_rows)
    W_skew = pow(W_variance, (-3 / 2)) * (W_prime_sum_of_cubes / total_rows)

    # Calculation of Kurtosis
    U_kurtosis = pow(U_variance, (-2)) * (U_prime_sum_of_quads / total_rows)
    V_kurtosis = pow(V_variance, (-2)) * (V_prime_sum_of_quads / total_rows)
    W_kurtosis = pow(W_variance, (-2)) * (W_prime_sum_of_quads / total_rows)

    # Calculation of Reynolds shear stress
    Reynolds_shear_stress_uv = (Reynolds_shear_stress_uv / total_rows)
    Reynolds_shear_stress_uw = (Reynolds_shear_stress_uw / total_rows)
    Reynolds_shear_stress_vw = (Reynolds_shear_stress_vw / total_rows)

    # Turbulent Kinetic Energy [TKE]
    TKE = 0.5*(U_variance + V_variance + W_variance)

    # Print results of each calculated statistical quantities in output window
    print("\nResults for file: %s" % table)

    print("Mean U velocity: %0.10f" % average_velocity_U)
    print("Mean V velocity: %0.10f" % average_velocity_V)
    print("Mean W velocity: %0.10f" % average_velocity_W)

    print("U variance: %0.10f" % U_variance)
    print("V variance: %0.10f" % V_variance)
    print("W variance: %0.10f" % W_variance)

    print("U standard deviation: %0.10f" % U_stdev)
    print("V standard deviation: %0.10f" % V_stdev)
    print("W standard deviation: %0.10f" % W_stdev)

    print("U skewness: %0.10f" % U_skew)
    print("V skewness: %0.10f" % V_skew)
    print("W skewness: %0.10f" % W_skew)

    print("U kurtosis: %0.10f" % U_kurtosis)
    print("V kurtosis: %0.10f" % V_kurtosis)
    print("W kurtosis: %0.10f" % W_kurtosis)

    print("UV Reynolds shear stress : %0.10f" % Reynolds_shear_stress_uv)
    print("UW Reynolds shear stress : %0.10f" % Reynolds_shear_stress_uw)
    print("VW Reynolds shear stress : %0.10f" % Reynolds_shear_stress_vw)

    print("TKE-Turbulent Kinetic Energy: %f" % TKE)

    if choice == 1:
      file_name = table
    elif choice == 2:
      file_name = f'{table}_{value_1:.4f}_to_{value_2:.4f}'

    cursor = sqlcon.cursor()

    # === Create a new table ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Statistical_quantities (
        Table_name TEXT, 
        Mean_U REAL, 
        Mean_V REAL, 
        Mean_W REAL, 
        U_variance REAL, 
        V_variance REAL,
        W_variance REAL, 
        U_stdev REAL, 
        V_stdev REAL, 
        W_stdev REAL, 
        U_skew REAL, 
        V_skew REAL, 
        W_skew REAL, 
        U_kurtosis REAL,
        V_kurtosis REAL, 
        W_kurtosis REAL, 
        Reynolds_shear_stress_uv REAL, 
        Reynolds_shear_stress_uw REAL,
        Reynolds_shear_stress_vw REAL, 
        TKE REAL
    )
    ''')
    # === Inset the data into the table ===
    cursor.execute('''
    INSERT INTO Statistical_quantities (Table_name, Mean_U, Mean_V, Mean_W, 
                U_variance, V_variance, W_variance, U_stdev, V_stdev, W_stdev, U_skew, V_skew, W_skew, U_kurtosis, 
                V_kurtosis, W_kurtosis, Reynolds_shear_stress_uv, Reynolds_shear_stress_uw, Reynolds_shear_stress_vw, 
                TKE)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (file_name, average_velocity_U, average_velocity_V, average_velocity_W, U_variance,
                V_variance, W_variance, U_stdev, V_stdev, W_stdev, U_skew, V_skew, W_skew, U_kurtosis, V_kurtosis,
                W_kurtosis, Reynolds_shear_stress_uv, Reynolds_shear_stress_uw, Reynolds_shear_stress_vw, TKE))
    sqlcon.commit()
    print("--------------------------------------------------------------------------------------------------------")


# Fast fourier transform of instantaneous velocities calculation and creation of amplitude spectra
def fft_velocities_calc(sqlcon, all_tab_names):
  """ (sqlite3.connections, list of strings)
      Get 'columns' from the tables 'all_tab_names' in the database connected by'sqlcon'.
      Calculates FFT of data, generates amplitude spectra and stores in a folder

      Before using this function make sure to use the function: tracking_multiple_data_to_db(dbname, input_files)
      if there is no instantaneous velocity data in a database
  """

  import matplotlib.pyplot as plt
  from scipy.fftpack import fft
  from matplotlib import rc
  import os
  import sqlite3
  import sys
  from pathlib import Path
  import numpy as np

  all_fft_tables = []
  column_header = ["time", "velocity_phy_01", "velocity_phy_02", "velocity_phy_03"]
  for name in all_tab_names:
    fft_folder = f'{name}_FFT'
    all_fft_tables.append(fft_folder)
    if not os.path.exists(f'{fft_folder}'):
      os.makedirs(f'{fft_folder}')
      print(f'\n{fft_folder} folder created')
    print(f"\n Calculating FFT for the instantaneous velocties (u,v,w) from the table:{name}")

    t, column_as_array_U, column_as_array_V, column_as_array_W = get_columns(sqlcon, tabname=name,
                                                                                     columns=column_header,
                                                                                     as_nparray=True)
    percentage = float(
      input(
        "Enter the % number of samples for FFT Calculation (default 100 percent). Press Enter to accept default : ")
      or "100")
    t_iter = np.subtract(t[2], t[1])
    freq_from_data = round(1 / t_iter)
    print(f"Recommended sampling frequency for {name}:", freq_from_data)
    frequency = int(input("Enter the sampling frequency: "))
    print(f"\nTaking the instantaneous velocity values from table:{name} ")

    array_size = column_as_array_U.size

    slice_of_input_array_for_processing_FFT_U = []
    slice_of_input_array_for_processing_FFT_V = []
    slice_of_input_array_for_processing_FFT_W = []

    N = int(array_size * (percentage / 100))

    # num_samples = 3000
    for i in range(0, N):
      slice_of_input_array_for_processing_FFT_U.append(column_as_array_U[i])
      slice_of_input_array_for_processing_FFT_V.append(column_as_array_V[i])
      slice_of_input_array_for_processing_FFT_W.append(column_as_array_W[i])

    # Creating the plots of Fourier Averaging of Velocities
    fig, axs = plt.subplots(2, 2, sharex=True, sharey=True)
    # frequency of signal
    T = 1 / frequency
    # x=np.linspace(0,N*T,N)#0, ,21
    y = slice_of_input_array_for_processing_FFT_U
    ####### processs via window  y = windowing(y)
    yf = fft(y)
    xf = np.linspace(0.0, 1.0 / (2 * T), N // 2)  # 0, ,10
    my_list = 2.0 / N * np.abs(yf[0:N // 2])
    my_list_u = my_list
    axs[0, 0].loglog(xf, my_list_u, color="r", label=r'Spectrum of $U$')
    axs[0, 0].set_ylabel(r'$U$-Amplitude [$\mathrm{m/s}$]')
    axs[0, 0].grid()
    axs[0, 0].legend()

    y = slice_of_input_array_for_processing_FFT_V
    ####### processs via window  y = windowing(y)
    yf = fft(y)
    my_list = 2.0 / N * np.abs(yf[0:N // 2])
    my_list_v = my_list
    axs[0, 1].loglog(xf, my_list_v, color="g", label=r'Spectrum of $V$')
    axs[0, 1].set_ylabel(r'$V$-Amplitude [$\mathrm{m/s}$]')
    axs[0, 1].grid()
    axs[0, 1].legend()

    y = slice_of_input_array_for_processing_FFT_W
    ####### processs via window  y = windowing(y)
    yf = fft(y)
    my_list = 2.0 / N * np.abs(yf[0:N // 2])
    my_list_w = my_list
    axs[1, 0].loglog(xf, my_list_w, color="b", label=r'Spectrum of $W$')
    axs[1, 0].set_xlabel(r'Frequency [Hz]')
    axs[1, 0].set_ylabel(r'$W$-Amplitude [$\mathrm{m/s}$]')
    axs[1, 0].grid()
    axs[1, 0].legend()

    axs[1, 1].loglog(xf, my_list_u, color="r", label=r'Spectrum of $U$')
    axs[1, 1].loglog(xf, my_list_v, color="g", label=r'Spectrum of $V$')
    axs[1, 1].loglog(xf, my_list_w, color="b", label=r'Spectrum of $W$')
    axs[1, 1].set_xlabel(r'Frequency [Hz]')
    axs[1, 1].set_ylabel(r'Amplitudes [$\mathrm{m/s}$]')
    axs[1, 1].grid()
    axs[1, 1].legend()

    image_filename_write = f'{fft_folder}/{name}_FFT_Spectra_Merged_UVW.jpg'
    imagename_without_extension = Path(image_filename_write).stem
    plot_title = (f'{imagename_without_extension} for '
                  f'\n{percentage}% data and sampling frequency {frequency}')
    # imagename_without_extension = imagename_without_extension.replace('_p00000', '')
    fig.suptitle(plot_title, fontsize=10)
    plt.tight_layout()
    plt.savefig(image_filename_write, dpi=300)
    plt.close()

    col_header = ['U', 'V', 'W']
    colors = ["red", "green", "blue"]
    my_list = [my_list_u, my_list_v, my_list_w]

    for c_h, cl, m_l in zip(col_header, colors, my_list):
      image_filename_write = f'{fft_folder}/{name}_{c_h}_FFT_Spectra.jpg'

      # image_filename_write = name + '_' + column_header_ind + '_FFT_Spectra.jpg'
      imagename_without_extension = Path(image_filename_write).stem

      # imagename_without_extension =  imagename_without_extension.replace('_p00000', '')

      plot_title = (f'{imagename_without_extension} for '
                    f'\n{percentage}% data and sampling frequency {frequency}')

      plt.loglog(xf, m_l, color=cl, label=rf'Spectrum of ${c_h}$')
      plt.legend()
      plt.grid()
      plt.xlabel('Frequency [Hz]')
      plt.ylabel(rf'${c_h}$-Amplitude [m/s]')
      plt.suptitle(plot_title, fontsize=10)
      plt.savefig(image_filename_write, dpi=300)
      # plt.show()
      plt.close()

    cursor = sqlcon.cursor()
    drop_existing(cursor, tabname=f"{name}_FFT_uvw")

    rows_to_insert = list(zip(xf, my_list_u, my_list_v, my_list_w))

    cursor.execute(f'''
               CREATE TABLE IF NOT EXISTS "{name}_FFT_uvw" (
                   Frequency REAL,
                   Amplitude_U REAL,
                   Amplitude_V REAL,
                   Amplitude_W REAL
               )
               ''')
    cursor.executemany(f'''
               INSERT INTO "{name}_FFT_uvw" (Frequency, Amplitude_U, Amplitude_V, Amplitude_W)
               VALUES (?, ?, ?, ?)
               ''', rows_to_insert)

    # === STEP 4: Commit and close ===
    sqlcon.commit()

    print(f"\nProcessing complete. Calculated Fast Fourier Transform of velocities, generated plots of spectra and "
          f"\nthey are saved to the folder {fft_folder}")
    print("--------------------------------------------------------------------------------------------------------")
######################################################################################################################


################## Cumulative means and variances calculation and creation of plots ##################################
def cumulative_mean_var_calc(sqlcon, all_tab_names):
  """ (sqlite3.Connection, list of strings)
      Get column values from the tables 'all_tab_names' in the database connected by 'sqlcon'

      Calculates cumulative means and variances and data are stored in each table names

      Before using this function make sure to use the function: tracking_multiple_data_to_db(dbname, input_files)
      if there is no instantaneous velocity data in a database
  """
  no_of_files = len(all_tab_names)
  col_head = ['time', 'velocity_phy_01', 'velocity_phy_02', 'velocity_phy_03']
  for table, i in zip(all_tab_names, range(no_of_files)):
    t, u, v, w = get_columns(sqlcon, tabname=table, columns=col_head)

    run_mean_U = []
    u_var = []
    inst_velocity_U = 0
    u_var_ind = 0

    run_mean_V = []
    v_var = []
    inst_velocity_V = 0
    v_var_ind = 0

    run_mean_W = []
    w_var = []
    inst_velocity_W = 0
    w_var_ind = 0

    for i in range(len(u)):
      inst_velocity_U += u[i]
      u_mean_ind = inst_velocity_U / (i + 1)
      run_mean_U.append(u_mean_ind)
      u_fluc = u[i] - u_mean_ind
      u_var_ind += u_fluc * u_fluc
      u_var_ind_i = u_var_ind / (i + 1)
      u_var.append(u_var_ind_i)

      inst_velocity_V += v[i]
      v_mean_ind = inst_velocity_V / (i + 1)
      run_mean_V.append(v_mean_ind)
      v_fluc = v[i] - v_mean_ind
      v_var_ind += v_fluc * v_fluc
      v_var_ind_i = v_var_ind / (i + 1)
      v_var.append(v_var_ind_i)

      inst_velocity_W += w[i]
      w_mean_ind = inst_velocity_W / (i + 1)
      run_mean_W.append(w_mean_ind)
      w_fluc = w[i] - w_mean_ind
      w_var_ind += w_fluc * w_fluc
      w_var_ind_i = w_var_ind / (i + 1)
      w_var.append(w_var_ind_i)

    rows_to_insert = list(zip(t, run_mean_U, run_mean_V, run_mean_W, u_var, v_var, w_var))
    cursor = sqlcon.cursor()
    drop_existing(cursor, tabname=f'{table}_cumulative_mean_var')
    # === Create a new table ===
    cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {table}_cumulative_mean_var (
                    time REAL,
                    Mean_U REAL,
                    Mean_V REAL,
                    Mean_W REAL,
                    Variance_U REAL,
                    Variance_V REAL,
                    Variance_W REAL
                    )
                    ''')

    cursor.executemany(f'''
                    INSERT INTO {table}_cumulative_mean_var (time, Mean_U, Mean_V, Mean_W, Variance_U, 
                    Variance_V, Variance_W)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', rows_to_insert)
    sqlcon.commit()


def plot_cumulative_mean_var(sqlcon, all_tab_names):
  """ (sqlite3.Connection, list of strings)
      Get column values from the tables 'all_tab_names' in the database connected by 'sqlcon'.

      The database also contains cumulative means and variances stored under each table names

      Creates the cumulative means and variances plots and stored in each folder
  """
  import matplotlib.pyplot as plt
  import matplotlib.ticker as ticker
  import os

  no_of_files = len(all_tab_names)
  col_head = ['velocity_phy_01', 'velocity_phy_02', 'velocity_phy_03']
  cum_col_head = ['time', 'Mean_U', 'Mean_V', 'Mean_W', 'Variance_U', 'Variance_V', 'Variance_W']
  all_data_folders = []
  for table, i in zip(all_tab_names, range(no_of_files)):
    cum_table = f'{table}_cumulative_mean_var'
    [t, run_mean_U, run_mean_V, run_mean_W, u_var, v_var, w_var] = get_columns(sqlcon, tabname=cum_table,
                                                                               columns=cum_col_head)
    [u, v, w] = get_columns(sqlcon, tabname=table, columns=col_head)

    data_folder_ind = f"Cumu_{table}"
    if not os.path.exists(f'{data_folder_ind}'):
      os.makedirs(f'{data_folder_ind}')
      print(f'\n{data_folder_ind} folder created')

    all_data_folders.append(data_folder_ind)

    fig, ax = plt.subplots()
    # color = 'tab:blue'f
    ax.plot(t, u, color="tab:blue", label=f'Inst. velocity-$U$')
    ax.plot(t, run_mean_U, color="r", label=r'Mean velocity-$\overline{U}$')
    ax.legend()
    ax.set_xlabel('Time [s]')
    ax.set_ylabel(r'$U, \overline{U}$ [m/s]')
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
    ax.grid(axis='x')
    #plt.show()
    fig.savefig(f"{data_folder_ind}/U_inst_u_mean_comparison_plot.jpg", dpi=300)
    plt.clf()
    plt.close()

    all_vel = [u, v, w]
    all_mean = [run_mean_U, run_mean_V, run_mean_W]
    all_var = [u_var, v_var, w_var]

    inst_dir = ['U', 'V', 'W']
    mean_dir = [r"$\overline{U}$", r"$\overline{V}$", r"$\overline{W}$"]
    var_dir = [r"$\overline{{u'}^2}$", r"$\overline{{v'}^2}$", r"$\overline{{w'}^2}$"]

    for inst, mean, var, i_dir, m_dir, v_dir in zip(all_vel, all_mean, all_var, inst_dir, mean_dir, var_dir):
      fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
      ax1.plot(t, inst, color="tab:blue", linewidth=1)
      ax1.set_xlabel('Time [s]')
      ax1.set_ylabel(rf'Inst. velocity-${i_dir}$ [m/s]')
      ax1.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
      ax1.grid(axis='x')
      ylim_inst = ax1.get_ylim()
      color = 'tab:red'
      ax2.plot(t, mean, color=color)
      ax2.set_xlabel('Time [s]')

      ax2.set_ylabel(f'Mean velocity-{m_dir} [m/s]', color=color)
      ax2.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
      ax2.grid(axis='x')
      ax2.tick_params(axis='y', labelcolor=color)
      ax2.set_ylim(ylim_inst)

      ax3 = ax2.twinx()  # instantiating a second Axes that shares the same x-axis
      color = 'tab:green'
      ax3.set_ylabel(f"Variance-{v_dir} [$m^2/s^2$]", color=color)  # we already handled the x-label with ax1
      ax3.plot(t, var, color=color)
      # ax2.set_ylim(0, 0.03)
      ax3.tick_params(axis='y', labelcolor=color)
      fig2.savefig(f"{data_folder_ind}/{table}_{i_dir}.jpg", dpi=300)
      plt.close(fig2)
    print(f'Plots are stored in the folder: Cumu_{table}')
  print('-------------------------------------------------------------------------------------------------------')
######################################################################################################################


################# Simple moving averages and variances calculation and creation of plots #############################
def simple_moving_avg_var_calc(sqlcon, all_tab_names):
  """ (sqlite3.Connection, list of strings)
      Get column values from the tables 'all_tab_names' in the database connected by 'sqlcon'

      Calculates simple moving means and variances and data are stored in each table names

      Before using this function make sure to use the function: tracking_multiple_data_to_db(dbname, input_files)
      if there is no instantaneous velocity data in a database
  """
  import matplotlib.pyplot as plt
  import numpy as np
  import matplotlib.ticker as ticker

  no_of_files = len(all_tab_names)
  col_head = ['time', 'velocity_phy_01', 'velocity_phy_02', 'velocity_phy_03']
  for table, i in zip(all_tab_names, range(no_of_files)):
    t, u, v, w = get_columns(sqlcon, tabname=table, columns=col_head)
    print(f'No. of instances of U-velocity for {table}:', len(u))

    while True:

      window_size = int(input(f"\nEnter the window size for the {table}:"))

      len_u = len(u)
      length = len_u - window_size + 1

      u_mean = []
      u_var = []
      for i in range(length):
        a = i
        b = window_size + i
        win_avg = np.average(u[a:b])
        win_avg = np.round(win_avg, 6)
        u_mean.append(win_avg)

        u_fluc = np.subtract(u[a:b], win_avg)
        u_prime_sq = u_fluc * u_fluc
        u_prime_sq_avg = np.average(u_prime_sq)
        u_prime_sq_avg = np.round(u_prime_sq_avg, 6)
        u_var.append(u_prime_sq_avg)

      t_red = t[window_size - 1:len_u]

      fig, ax = plt.subplots()
      ax.plot(t, u, color="tab:blue", label=r'Inst. velocity-$U$')
      ax.plot(t_red, u_mean, color="r", label=r'Mean velocity-$\overline{U}$')
      ax.legend()
      ax.set_xlabel('Time [s]')
      ax.set_ylabel(r'$U$, $\overline{U}$ [m/s]')
      ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
      ax.grid(axis='x')
      plt.show()
      plt.close(fig)

      print("Is the Mean velocity-U plot and the chosen window size okay?. Select the choices below")
      print("Choice 1: Yes. Proceed to calculate mean and variance from Inst. velocity-V and W")
      print("Choice 2: No. Change the window size and create Mean velocity-U plot again")
      choice = int(input("\nSelect your choice (Type 1 or 2): "))
      match choice:
        case 1:
          print("Proceeded to calculate mean and variance from Inst. velocity-V and W")
          break
        case 2:
          print("Okay. Change the window size.")
        case _:
          print("\nInvalid number. Try again")

    v_mean = []
    v_var = []
    w_mean = []
    w_var = []
    for i in range(length):
      a = i
      b = window_size + i
      win_avg = np.average(v[a:b])
      win_avg = np.round(win_avg, 6)
      v_mean.append(win_avg)

      v_fluc = np.subtract(v[a:b], win_avg)
      v_prime_sq = v_fluc * v_fluc
      v_prime_sq_avg = np.average(v_prime_sq)
      v_prime_sq_avg = np.round(v_prime_sq_avg, 6)
      v_var.append(v_prime_sq_avg)

      win_avg = np.average(w[a:b])
      win_avg = np.round(win_avg, 6)
      w_mean.append(win_avg)

      w_fluc = np.subtract(w[a:b], win_avg)
      w_prime_sq = w_fluc * w_fluc
      w_prime_sq_avg = np.average(w_prime_sq)
      w_prime_sq_avg = np.round(w_prime_sq_avg, 6)
      w_var.append(w_prime_sq_avg)

    rows_to_insert = list(zip(t_red, u_mean, v_mean, w_mean, u_var, v_var, w_var))
    cursor = sqlcon.cursor()
    drop_existing(cursor, tabname=f'{table}_mov_window_mean_var')
    # === Create a new table ===
    cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {table}_simple_moving_mean_var (
                    time_red REAL,
                    Mean_U REAL,
                    Mean_V REAL,
                    Mean_W REAL,
                    Variance_U REAL,
                    Variance_V REAL,
                    Variance_W REAL
                    )
                    ''')

    cursor.executemany(f'''
                    INSERT INTO {table}_simple_moving_mean_var (time_red, Mean_U, Mean_V, Mean_W, Variance_U, 
                    Variance_V, Variance_W)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', rows_to_insert)
    sqlcon.commit()


def plot_simple_moving_avg_var(sqlcon, all_tab_names):
  """ (sqlite3.Connection, list of strings)
      Get column values from the tables 'all_tab_names' in the database connected by 'sqlcon'.
`
      The database also contains simple moving means and variances stored under each table names

      Creates the simple moving means and variances plots and stored in each folder
  """
  import matplotlib.pyplot as plt
  import matplotlib.ticker as ticker
  import os

  no_of_files = len(all_tab_names)
  moving_col_head = ['time_red', 'Mean_U', 'Mean_V', 'Mean_W', 'Variance_U', 'Variance_V', 'Variance_W']
  col_head = ['time', 'velocity_phy_01', 'velocity_phy_02', 'velocity_phy_03']
  all_data_folders = []
  for table, i in zip(all_tab_names, range(no_of_files)):
    moving_table = f'{table}_simple_moving_mean_var'
    [t_red, u_mean, v_mean, w_mean, u_var, v_var, w_var] = get_columns(sqlcon, tabname=moving_table,
                                                                               columns=moving_col_head)
    [t, u, v, w] = get_columns(sqlcon, tabname=table, columns=col_head)

    data_folder_ind = f"Sma_{table}"
    if not os.path.exists(f'{data_folder_ind}'):
      os.makedirs(f'{data_folder_ind}')
      print(f'\n{data_folder_ind} folder created')

    all_data_folders.append(data_folder_ind)

    fig, ax = plt.subplots()
    ax.plot(t, u, color="tab:blue", label=r'Inst. velocity-$U$')
    ax.plot(t_red, u_mean, color="r", label=r'Mean velocity-$\overline{U}$')
    ax.legend()
    ax.set_xlabel('Time [s]')
    ax.set_ylabel(r'$U$, $\overline{U}$ [m/s]')
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
    ax.grid(axis='x')
    fig.savefig(f"{data_folder_ind}/U_inst_u_mean_comparison_plot.jpg", dpi=300)
    plt.close(fig)

    all_vel = [u, v, w]
    all_mean = [u_mean, v_mean, w_mean]
    all_var = [u_var, v_var, w_var]
    inst_dir = ['U', 'V', 'W']
    mean_dir = [r"$\overline{U}$", r"$\overline{V}$", r"$\overline{W}$"]
    var_dir = [r"$\overline{{u'}^2}$", r"$\overline{{v'}^2}$", r"$\overline{{w'}^2}$"]

    for inst, mean, var, i_dir, m_dir, v_dir in zip(all_vel, all_mean, all_var, inst_dir, mean_dir, var_dir):
      fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
      ax1.plot(t, inst, color="tab:blue", linewidth=1)
      ax1.set_xlabel('Time [s]')
      ax1.set_ylabel(rf'Inst. velocity-${i_dir}$ [m/s]')
      ax1.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
      ax1.grid(axis='x')
      ylim_inst = ax1.get_ylim()
      xlim_inst = ax1.get_xlim()

      color = 'tab:red'
      ax2.plot(t_red, mean, color=color)
      ax2.set_xlabel('Time [s]')
      ax2.set_ylabel(f'Mean velocity-{m_dir} (m/s)', color=color)
      ax2.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
      ax2.grid(axis='x')
      ax2.tick_params(axis='y', labelcolor=color)
      ax2.set_xlim(xlim_inst)
      ax2.set_ylim(ylim_inst)

      ax3 = ax2.twinx()  # instantiating a second Axes that shares the same x-axis
      color = 'tab:green'
      ax3.set_ylabel(f"Variance-{v_dir} [$m^2/s^2$]", color=color)  # we already handled the x-label with ax1
      ax3.plot(t_red, var, color=color)
      ax3.set_ylim(min(var) * 0.005, max(var) * 3) ### set ylim as per your need ##
      ax3.tick_params(axis='y', labelcolor=color)
      fig2.savefig(f"{data_folder_ind}/{table}_{i_dir}.jpg", dpi=300)
      plt.close(fig2)
    print(f'Plots are stored in the folder: Sma_{table}')
  print('-------------------------------------------------------------------------------------------------------')
######################################################################################################################


####################### Fourier means and variances calculation and creation of plots ################################
def calc_ak_bk(U, total_rows, k):
  '''
  (array of floats, int, int)
  U -array of fluctuating velocity component
  total_rows - Total no. of values of a single instantaneous quantity over a period of time,

  calc_ak_bk calculates the summation of coefficients for the Fourier Averaging. k represents no. of
  fourier components
  '''

  import numpy as np
  import math

  ak = bk = 0
  j = 0
  for every_value in U:
    ak = ak + every_value * np.cos(2 * math.pi * (j / total_rows) * k)
    bk = bk + every_value * np.sin(2 * math.pi * (j / total_rows) * k)
    j += 1
  return ak / total_rows, bk / total_rows


def all_fourier_calculations(total_rows, U, V, W, M):
  """ (int, array of floats, array of floats, array of floats, int)
      total_rows - Total no. of values of a single instantaneous quantity over a period of time,
      U, V, W - array of fluctuating velocity components, M - No. of Fourier components to average

      all_fourier_calculations performs the Fourier averaging of velocities and returns the
      Unsteady average quantities
  """
  import numpy as np
  import math

  U0 = np.mean(U)
  V0 = np.mean(V)
  W0 = np.mean(W)

  U_avg = []
  partial_sum_U = 0
  V_avg = []
  partial_sum_V = 0
  W_avg = []
  partial_sum_W = 0

  ak_list_U = []
  bk_list_U = []
  ak_list_V = []
  bk_list_V = []
  ak_list_W = []
  bk_list_W = []

  for k in range(1, int((M - 1) / 2) + 1):
    ak_U, bk_U = calc_ak_bk(U, total_rows, k)
    ak_list_U.append(ak_U)
    bk_list_U.append(bk_U)
    ak_V, bk_V = calc_ak_bk(V, total_rows, k)
    ak_list_V.append(ak_V)
    bk_list_V.append(bk_V)
    ak_W, bk_W = calc_ak_bk(W, total_rows, k)
    ak_list_W.append(ak_W)
    bk_list_W.append(bk_W)

  # print ak_list_U, bk_list_U, ak_list_V, bk_list_V, ak_list_W, bk_list_W,

  for j in range(0, total_rows):
    # print "---------------\nIteration Number J = %d" %(j)
    for k in range(1, int((M - 1) / 2) + 1):
      partial_sum_U = partial_sum_U + ak_list_U[k - 1] * np.cos(2 * math.pi * (j / total_rows) * k) + bk_list_U[
        k - 1] * np.sin(2 * math.pi * (j / total_rows) * k)
      partial_sum_V = partial_sum_V + ak_list_V[k - 1] * np.cos(2 * math.pi * (j / total_rows) * k) + bk_list_V[
        k - 1] * np.sin(2 * math.pi * (j / total_rows) * k)
      partial_sum_W = partial_sum_W + ak_list_W[k - 1] * np.cos(2 * math.pi * (j / total_rows) * k) + bk_list_W[
        k - 1] * np.sin(2 * math.pi * (j / total_rows) * k)
    U_j = 0.5 * U0 + partial_sum_U
    V_j = 0.5 * V0 + partial_sum_V
    W_j = 0.5 * W0 + partial_sum_W
    # print "U_avg = %f" %(U_j*2)  # Multiplied by 2 since Vishal had 2/n and  1 * a0
    partial_sum_U = 0
    partial_sum_V = 0
    partial_sum_W = 0
    U_avg.append(float('{:01.6f}'.format(U_j * 2))) # rounded to three decimal spaces, change if you want
    V_avg.append(float('{:01.6f}'.format(V_j * 2)))
    W_avg.append(float('{:01.6f}'.format(W_j * 2)))

  return U_avg, V_avg, W_avg


# Use this function for calculation of fourier means and variances
def fourier_mean_var_calc(sqlcon, all_tab_names):
  """ (sqlite3.Connection, list of strings)
      Get column values from the tables 'all_tab_names' in the database connected by 'sqlcon'

      Calculates fourier means and variances and data are stored in each table names

      Before using this function make sure to use the function: tracking_multiple_data_to_db(dbname, input_files)
      if there is no instantaneous velocity data in a database
    """
  import matplotlib.pyplot as plt
  import matplotlib.ticker as ticker

  no_of_files = len(all_tab_names)
  col_head = ['time', 'velocity_phy_01', 'velocity_phy_02', 'velocity_phy_03']
  for table, i in zip(all_tab_names, range(no_of_files)):
    t, u, v, w = get_columns(sqlcon, tabname=table, columns=col_head)
    total_rows = len(u)
    print(f'No. of instances of U-velocity for {table}:', total_rows)

    while True:

      # Taking No. of Fourier components as input from user
      M = int(input("Unsteady flow: Enter the value of k, i.e. # of Fourier Components : "))
      while (M % 2 != 1):
        print("The Value of k should be strictly odd")
        M = int(input("Enter the value of k, i.e. # of Fourier Components : "))

      U_avg, V_avg, W_avg = all_fourier_calculations(total_rows, u, v, w, M)

      fig, ax = plt.subplots()
      ax.plot(t, u, color="b", label=r'Inst. Velocity-$U$')
      ax.plot(t, U_avg, color="r", label=r'Mean Velocity-$\overline{U}$')
      ax.legend()
      ax.set_xlabel('Time [s]')
      ax.set_ylabel(r'$U$, $\overline{U}$ [m/s]')
      ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
      ax.grid(axis='x')
      plt.show()
      plt.close(fig)

      print("Is the Mean velocity-U plot and the chosen No. of fourier components (k) okay? "
            "\nSelect the choices below")
      print("Choice 1: Yes. Proceed to calculate mean velocities V and W plots and Variances")
      print("Choice 2: No. Need to change the No. of fourier components (k) and create "
            "Mean velocity-U plot again")
      choice = int(input("\nSelect your choice (Type 1 or 2): "))
      match choice:
        case 1:
          print("Proceeded to calculate mean velocities V and W and Variances")
          break
        case 2:
          print("Okay. Change the No. of fourier components (k)")
        case _:
          print("\nInvalid number. Try again")

    # plot fourier average and variances
    U_prime_U_prime = []
    V_prime_V_prime = []
    W_prime_W_prime = []

    for a, b, c, d, e, f in zip(u, U_avg, v, V_avg, w, W_avg):
      U_prime_U_prime.append(float('{:01.3f}'.format((a - b) * (a - b))))
      V_prime_V_prime.append(float('{:01.3f}'.format((c - d) * (c - d))))
      W_prime_W_prime.append(float('{:01.3f}'.format((e - f) * (e - f))))

    u_var, v_var, w_var = all_fourier_calculations(total_rows, U_prime_U_prime, V_prime_V_prime, W_prime_W_prime,
                                                   M)
    rows_to_insert = list(zip(t, U_avg, V_avg, W_avg, u_var, v_var, w_var))
    cursor = sqlcon.cursor()
    drop_existing(cursor, tabname=f'{table}_fourier_mean_var')
    # === Create a new table ===
    cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table}_fourier_mean_var (
                time REAL,
                Mean_U REAL,
                Mean_V REAL,
                Mean_W REAL,
                Variance_U REAL,
                Variance_V REAL,
                Variance_W REAL
                )
                ''')

    cursor.executemany(f'''
                INSERT INTO {table}_fourier_mean_var (time, Mean_U, Mean_V, Mean_W, Variance_U, 
                Variance_V, Variance_W)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', rows_to_insert)
    sqlcon.commit()


def plot_fourier_mean_var(sqlcon, all_tab_names):
  """ (sqlite3.Connection, list of strings)
      Get column values from the tables 'all_tab_names' in the database connected by 'sqlcon'.
`
      The database also contains fourier means and variances stored under each table names

      Creates the fourier means and variances plots and stored in each folder
  """
  import matplotlib.pyplot as plt
  import matplotlib.ticker as ticker
  import os

  no_of_files = len(all_tab_names)
  fourier_col_head = ['time', 'Mean_U', 'Mean_V', 'Mean_W', 'Variance_U', 'Variance_V', 'Variance_W']
  col_head = ['velocity_phy_01', 'velocity_phy_02', 'velocity_phy_03']
  all_data_folders = []
  for table, i in zip(all_tab_names, range(no_of_files)):
    fourier_table = f'{table}_fourier_mean_var'
    [t, U_avg, V_avg, W_avg, u_var, v_var, w_var] = get_columns(sqlcon, tabname=fourier_table,
                                                                       columns=fourier_col_head)
    [u, v, w] = get_columns(sqlcon, tabname=table, columns=col_head)

    fig, ax = plt.subplots()
    ax.plot(t, u, color="b", label=r'Inst. Velocity-$U$')
    ax.plot(t, U_avg, color="r", label=r'Mean Velocity-$\overline{U}$')
    ax.legend()
    ax.set_xlabel('Time [s]')
    ax.set_ylabel(r'$U$, $\overline{U}$ [m/s]')
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
    ax.grid(axis='x')

    data_folder_ind = f"Fourier_{table}"
    if not os.path.exists(f'{data_folder_ind}'):
      os.makedirs(f'{data_folder_ind}')
      print(f'\n{data_folder_ind} folder created')

    all_data_folders.append(data_folder_ind)

    fig.savefig(f"{data_folder_ind}/U_inst_u_mean_comparison_plot.jpg", dpi=300)
    plt.close(fig)

    all_vel = [u, v, w]
    all_mean = [U_avg, V_avg, W_avg]
    all_var = [u_var, v_var, w_var]
    inst_dir = ['U', 'V', 'W']
    mean_dir = [r"$\overline{U}$", r"$\overline{V}$", r"$\overline{W}$"]
    var_dir = [r"$\overline{{u'}^2}$", r"$\overline{{v'}^2}$", r"$\overline{{w'}^2}$"]

    for inst, mean, var, i_dir, m_dir, v_dir in zip(all_vel, all_mean, all_var, inst_dir, mean_dir, var_dir):
      fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
      ax1.plot(t, inst, color="tab:blue", linewidth=1)
      ax1.set_xlabel('Time [s]')
      ax1.set_ylabel(f'Inst. Velocity-{i_dir}')
      ax1.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
      ax1.grid(axis='x')
      ylim_inst = ax1.get_ylim()
      xlim_inst = ax1.get_xlim()
      color = 'tab:red'

      ax2.plot(t, mean, color=color)
      ax2.set_xlabel('Time [s]')
      ax2.set_ylabel(f'Mean velocity-{m_dir} (m/s)', color=color)
      ax2.xaxis.set_major_locator(ticker.MaxNLocator(nbins=7))
      ax2.grid(axis='x')
      ax2.tick_params(axis='y', labelcolor=color)
      ax2.set_xlim(xlim_inst)
      ax2.set_ylim(ylim_inst)

      ax3 = ax2.twinx()  # instantiating a second Axes that shares the same x-axis
      color = 'tab:green'
      ax3.set_ylabel(f"Variance-{v_dir} [$m^2/s^2$]", color=color)
      ax3.plot(t, var, color=color)
      ax3.set_ylim(min(var) * 0.005, max(var) * 3) ## you can change or remove the ylim as your wish ##
      # ax2.set_ylim(0, 0.03)
      ax3.tick_params(axis='y', labelcolor=color)
      fig2.savefig(f"{data_folder_ind}/{table}_{i_dir}.jpg", dpi=300)
      plt.close(fig2)
    print(f'Plots are stored in the folder: Fourier_{table}')
  print('-------------------------------------------------------------------------------------------------------')