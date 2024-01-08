usePeriodic = true
-- simulation domain settings
length = 200.0
level= 4
refinementLevel =  6
printRuntimeInfo = false

minlevel  = level
dx     = length/(2^refinementLevel)
dxDash = 0.001*dx
nElemsMax = 2^refinementLevel
folder = 'mesh/'
bounding_cube = {
  origin = { -length*0.5,-length*0.5,-length*0.5 },
  length = length,
}

spatial_object = {
  {
    attribute = {
      kind = 'refinement',
      level = refinementLevel,
      label='refine',
    },
    geometry = {
      kind = 'canoND',
      object = {
        origin = { -length*0.5, -length*0.5, -dxDash },
        vec = {
          { length, 0., 0.},
          { 0., length, 0.},
          { 0., 0,      dx},
        },
      }
    }
  },
  { attribute = { kind = 'seed', },
    geometry = { 
      kind = 'canoND',
      object = { origin = { 0.0, 0.0, 0 },
      }
    } 
  },
  {
    attribute = {
      kind = 'boundary',
      label='east',
      level= level
    },
    geometry = {
      kind = 'canoND',
      object = {
        origin = {length*0.5, -length*0.5, -dx*0.5},
        vec = {{0.0, length, 0.},
              {0.,0.0, dx}}
      }
    }
  },
  {
    attribute = {
      kind = 'boundary',
      label='west',
      level= level
    },
    geometry = {
      kind = 'canoND',
      object = {
        origin = {-length*0.5, -length*0.5, -dx*0.5},
        vec = {{0.0, length, 0.},
              {0.,0.0, dx}}
      }
    }
  },
  {
    attribute = {
      kind = 'boundary',
      label='north',
      level= level
    },
    geometry = {
      kind = 'canoND',
      object = {
        origin = {-length*0.5, length*0.5, -dx*0.5},
        vec = {{length, 0.0, 0.},
              {0.,0.0, dx}}
      }
    }
  },  
  {
    attribute = {
      kind = 'boundary',
      label='south',
      level= level
    },
    geometry = {
      kind = 'canoND',
      object = {
        origin = {-length*0.5,-length*0.5, -dx*0.5},
        vec = {{length, 0.0, 0.},
              {0.,0.0, dx}}
      }
    }
  }
}

if usePeriodic == true then
  table.insert(spatial_object, { 
    attribute = { kind = 'periodic', },
    geometry = {
      kind = 'periodic',
      object = {
        plane1 = {
          origin = { -length/2, -length/2, -dxDash},
          vec = { { length, 0.0, 0.0},
                  { 0.0, length, 0.0},}
        }, -- plane 1
        plane2 = {
          origin = { -length/2,  -length/2, dxDash +dx},
          vec = { { 0., length, 0.0, 0.0},
                  { length, 0., 0.0},}
        }, -- plane 2
      } -- object
    } -- geometry

  }) 
end

