-- Musubi configuration file. 
-- This is a LUA script.
originX = 0.0
originY = 0.0
originZ = 0.0
halfwidth = 3.0
amplitude = 0.1
background = 1.0

function ic_1Dgauss_pulse(x, y, z, t)
  return background+amplitude*math.exp(-math.log(2.)/(halfwidth^2)*( x - originX )^2)
end
function ic_2Dgauss_pulse(x, y, z, t)
  return background+amplitude*math.exp(-math.log(2.)/(halfwidth^2)*(( x - originX )^2+( y - originY )^2))
end
-- Initial condition 
initial_condition = { --density = {predefined='gausspulse', center={0.0,0.0,0.0}, halfwidth=0.3, amplitude=0.20, background=1.000},
                      pressure  = ic_2Dgauss_pulse,
                      velocityX = 0.0,
                      velocityY = 0.0,
                      velocityZ = 0.0 }
-- Simulation name
simulation_name = 'Gaussian_pulse_validation'
logging = {level=3}

mesh = 'mesh/'-- Mesh information

fluid = { omega = 1.98, rho0 = 1.0 }

-- Boundary conditions

-- Local refinement settings
interpolation_method = 'linear'
                     
-- Time step settigs
tmax           = 1000    -- total iteration number
check_interval = tmax/10   -- iteration check interval

sim_control = {
  time_control = {
    interval = {iter= check_interval},
    max = {iter = tmax}
  }
}

identify = {
  layout = 'd2q9',
  kind = 'lbm',
  relaxation = 'bgk'
}

-- Tracking              
tracking = {
 { label = 'probe_press', 
   variable = {'density'},
   shape = {
     kind = 'canoND',
     object = {
       origin = { 0.0, 0.,0.},
     }
   },
   time_control = {
     min = { iter= 1 },
     interval = { iter= 10 },
   },
   output = {format='ascii', use_get_point = true}, 
   folder='tracking/'
 },
 { label = 'line', 
   variable = {'density'}, -- state (=pdfs), pressure, density etc
   shape = {
     kind = 'canoND',
     object = {
       origin = { 0.0, 0.,0.},
       vec = {60., 0., 0.},
       segments = {200},
       distribution='equal',
     }
   },
   time_control = {
     min = { iter=  1},
     interval = {iter=10}
   },
   output = {format='asciiSpatial', use_get_point = true}, 
   folder='./tracking/', 
 },
-- { label = 'line', 
-- variables = {'state'}, -- state (=pdfs), pressure, density etc
-- type='line', line ={ 
--    origin = {-75.,-0.,0.}, 
--    direction = {150.,0,0.}, 
--    segments=300, 
--    distribution='equal'}, 
-- format='harvester', folder='tracking/', 
-- interval = 1, tmin = 0, tmax = 800 } 
 }

