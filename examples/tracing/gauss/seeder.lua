outputname = 'bulk'
outputpreview = false
folder = 'mesh/'

length=60.

-- stl_files: for each stl file put a table into
-- this table of tables. Or just a string for
-- the filname, if the other two parameters should
-- get the default: boundary_type = 1, fileformat = 'binary'
-- refinementlevel is the level to which the stl shall be refined
-- it is mandatory

minlevel = 8

deltax=2.*length/(2^minlevel)

bounding_cube = {origin = {-length,-length,-length},
                 length = 2.*length}

-- In spatial object define the seed and plane1 and plane2
spatial_object = {
  {
   attribute = {
      kind = 'seed',  ---- seed
    },               
    geometry = {
      kind = 'canoND',  -- in seed  kind is canoND
      object = {
        origin = {0.,0.,deltax*0.5}
        }
      }
   },
  {
   attribute = {
      kind = 'periodic',  -- in attribute kind is seed/boundary/periodic/refinement
    },               
     geometry = {
       kind = 'periodic',
       object = {
         plane1 = {
           origin = {-length,-length,deltax+0.01},
           vec = {{2.*length,0.0,0.0},
                  {0.0,2.*length,0.0}}  
           },  ----plane1
         plane2 = {
           origin = {-length,-length,-deltax*0.01},
           vec = {{2.*length,0.0,0.0},
                {0.0,2.*length,0.0}}
           } ----plane2
         }--- object
       } ---`geometry
     } ---attribute
   }  ---spatial object













