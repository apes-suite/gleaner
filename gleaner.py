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
