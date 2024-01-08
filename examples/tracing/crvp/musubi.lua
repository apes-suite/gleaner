require "seeder"

PI = math.pi
interpolation_method = 'linear'
simulation_name = 'crvp'
printRuntimeInfo = false
nRotations = 1
cutoff=true

tMax=1

-- Definition in physical units
Re   = 150   -- Reynold Number
Ma   = 0.095 -- Mach number
r0   = 1     -- [m] 
rho0 = 1     -- density
p0   = 1     -- background pressure
kappa = 1.4  -- isothermal exponent
csPhys     = math.sqrt(kappa*p0/rho0) -- speed of sound
u0 = Ma * csPhys  -- velocity magnitude in the vortex centers 
--u0 = 1  -- velocity magnitude in the vortex centers 
circulation =Ma*4*PI*r0*csPhys -- circulation
gamma = circulation
ang_vel= gamma/(4*PI*r0^2)          -- angular velocity 
T  = 2 * PI / ang_vel               -- circulation period
viscosity = circulation * rho0 / Re -- viscosity
Lamda = 2*PI*csPhys / ang_vel       -- wavelength
nearfar= Lamda*1.6
bc_type = 'outlet_nrbc'

-- Timings
tEnd  = nRotations * T  -- total time
interval = tEnd/50      -- interval for simulation 
-- Musubi configuration file. 
rho0LB = 1
cs2LB  = 1./3.
originX = 0.0
originY = 0.0
originZ = 0.0
origin = {originX, originY, originZ}

-- sponge should start at a radius of 85% from the origin
cutoff_rmin = 0.00
-- sponge should end  at a radius of 97% from the origin
cutoff_rmax = 0.10

-- Determine physical quantities
csLB = 1./math.sqrt(3.)
dt = csLB/csPhys*dx
viscLB = viscosity*dt/dx/dx
omega = 1./(3.*viscLB + 0.5)


-- Initial condition 
ini_pressure  = {predefined = "crvpPressure", 
                 radius_rot = r0,
                 t          = 0,
                 cs         = csPhys, 
                 p0         = p0,
                 --cutoff_length = length*0.5,
                 --cutoff_rmin   = cutoff_rmin,
                 --cutoff_rmax   = cutoff_rmax,
                 circulation   = circulation,
                 gpmodel=true,
                 center = origin} -- pressure
initial_condition = { 
  pressure = ini_pressure,
  velocityX = {  predefined = "crvpX", 
                 cs         = csPhys, 
                 radius_rot = r0,
                 circulation= circulation,
                 --cutoff_length = length*0.5,
                 --cutoff_rmin = cutoff_rmin,
                 --cutoff_rmax = cutoff_rmax,
                 center = origin },
  velocityY = {  predefined = "crvpY", 
                 cs         = csPhys, 
                 radius_rot = r0,
                 circulation= circulation,
                 --cutoff_length = length*0.5,
                 --cutoff_rmin = cutoff_rmin,
                 --cutoff_rmax = cutoff_rmax,
                 center = origin },
  velocityZ = 0.0   }
-- Simulation name
mesh = 'mesh/' -- Mesh information

fluid = { omega = omega, rho0 = rho0 }
identify = { kind = model, layout = 'd2q9', relaxation= 'bgk', }
physics = { dt = dt, rho0 = rho0, }


-- Boundary conditions
boundary_condition = {  
{ label = 'east',
   kind = bc_type,  pressure = p0, sigma = 0.001, kappa = 1.0, L = length*0.5 },
{ label = 'west',
   kind = bc_type, pressure = p0, sigma = 0.001, kappa = 1.0, L = length*0.5 },
{ label = 'north',
   kind = bc_type, pressure = p0, sigma = 0.001, kappa = 1.0, L = length*0.5 },
{ label = 'south',
   kind = bc_type, pressure = p0, sigma = 0.001, kappa = 1.0, L = length*0.5 }
}
                     

tMax = math.ceil(tEnd / dt)

-- Time step settigs
sim_control = {
  time_control = {
    max = {iter = tMax , clock = 7000},
    interval = {iter = interval}
  },
}


 -- Tracking              
 tracking = {
--  { label = 'stat_l'..level, 
--  variable = {'vel_mag'}, 
--  reduction = {'max'},
--  shape = {kind = 'all' },
--  time_control =  {
--    interval = {iter=20}, 
--    min = 0, 
--    max =tEnd, 
--  },
--  folder = './tracking/',
--  output = { format = 'ascii'},
--  },
--  { label = 'dens_l'..level, 
--  variable = {'density'}, 
--  shape = {
--    kind = 'canoND', 
--    object = {
--              origin = {-length*0.5,0.,0.}, 
--              vec = {length, 0.,0.}, 
--              segments = 2*nElemsMax 
--             } 
--          },
--   time_control = {interval = interval, min =0, max =tEnd},
--   folder = './tracking/',
--   output = { format = 'asciiSpatial'},
--  },
  { label = 'pressCutX_l'..level, 
  variable = {'pressure'}, 
  shape = {
    kind = 'canoND', 
    object = {
              origin = {-length*0.5,0.,0.}, 
              vec = {length, 0.,0.}, 
              segments = 2*nElemsMax 
             } 
          },
   time_control = {interval = interval, min =0, max =tEnd},
   folder = './tracking/',
   output = { format = 'asciiSpatial'},
  },
--  { label = 'hvs_l'..level, 
--  variable = {'pressure_phy','velocity_phy'}, 
--  shape = {kind = 'all'},
--  time_control =  {interval = interval ,  min = 0, max = tEnd }, 
--  folder = './tracking/',
--  output = { format = 'vtk'}
--  },
--  { label = 'probePressure_l'..level, 
--  variable = {'density','pressure_phy'}, 
--  shape = {
--    { kind = 'canoND', 
--      object = {origin ={1.,0.,0.} } }, 
--    { kind = 'canoND', 
--      object = {origin ={length*0.5*0.5,0.,0.} } }
--    },
--  time_control =  {interval ={iter= 1}, min = 0, max= tEnd }, 
--  folder = './tracking/',
--  output = {format = 'ascii'}
--  }
} 
