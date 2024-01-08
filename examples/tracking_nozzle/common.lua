--mesh parameters
-- length of the nozzle
l_nozzle = 20e-2 --m
-- outer diameter of nozzle
outer_dia_nozzle = 2e-2 --m
outer_rad_nozzle = outer_dia_nozzle*0.5
-- ratio of inner dia to outer dia
inner_to_outer_ratio = 0.5
-- inner diameter of nozzle
inner_dia_nozzle = outer_dia_nozzle*inner_to_outer_ratio
inner_rad_nozzle = inner_dia_nozzle*0.5
-- Origin of nozzle
origin_nozzle = {0.0,0.0,0.0}
-- position of inner diameter area in nozzle
l_neck = -5.0e-2
nozzle_inner_dia_X = l_neck

-- distance of inlet to nozzle center
inlet_2_nozzleCenter = l_nozzle/2.0
-- distance of outlet to nozzle center
outlet_2_nozzleCenter = l_nozzle/2.0

-- Length and height of free flow area
h_ch = outer_dia_nozzle
l_ch = inlet_2_nozzleCenter + outlet_2_nozzleCenter 

-- Number of elements in height of free flow area
nElems_h_ch = 64
-- element size 
dx = h_ch/nElems_h_ch
-- Number of elements in length
nLength = math.ceil(l_ch/dx)
-- Number of elements in bounding cube length
-- +2 for inlet and outlet plane
nLength_bnd = nLength+2
-- refinement level required to achieve nElems_h_ch
level = math.ceil(math.log(nLength_bnd)/math.log(2))
-- physical length of bounding cube
length_bnd = (2^level)*dx

--refinement box level around nozzle
refineLevel = level + 0
nozzleLevel = refineLevel + 0
dx_refine = length_bnd/2^refineLevel
-- smallest element size
dx_eps = length_bnd/2^(20)

dx_coarse = dx
dx_c_half = dx_coarse/2.0
dx_f_half = dx_refine/2.0
z_X = dx/2.0

-- nozzle inlet
inlet_nozzle = {-l_nozzle/2.0, -outer_rad_nozzle, z_X}
-- nozzle outlet
outlet_nozzle = {l_nozzle/2.0, -outer_rad_nozzle, z_X}

-- nozzle center 
center_nozzle_l = {nozzle_inner_dia_X, -inner_rad_nozzle, z_pos} 
center_nozzle_u = {nozzle_inner_dia_X, inner_rad_nozzle, z_pos} 

-- Origin of inlet BC
origin_inletBC = {-inlet_2_nozzleCenter - dx_c_half, -h_ch/2.0-dx_c_half, -h_ch/2.0-dx_c_half}

-- Origin of outlet BC
origin_outletBC = { outlet_2_nozzleCenter + dx_c_half, -h_ch/2.0- dx_c_half, -h_ch/2.0 - dx_c_half}

-- bounding cube origin
origin_boundCube = {-inlet_2_nozzleCenter - dx, 
                    -h_ch/2.0-dx, 
                    -dx-h_ch/2.0
                    }

-- offset for refinement box
offset_refine = 1.5*outer_dia_nozzle
-- z position of nozzle
nozzle_zPos = outer_rad_nozzle

-- q-value
qVal = true

-- Flow parameters 
-- Properties of air: https://en.wikipedia.org/wiki/Standard_sea_level
-- density
rho0_p = 1.225 --kg/m^3
--dynamic viscosity
mu = 1.789e-5 --Pa s
--kinematic viscosity
nu_phy = mu / rho0_p  --m^2/s
u_mean_phy = 0.5 --m/s
-- In 2D,
u_max_phy = 3*u_mean_phy/2.0 --m/s
-- In 3D,
--u_max_phy = 2*u_mean_phy --m/s

--Reynolds number
Re = outer_dia_nozzle*u_mean_phy/nu_phy
-- diffusive scaling
omega = 1.98
nu_L = (1.0/omega-0.5)/3.0
dt = nu_L*dx_coarse^2/nu_phy
u_max_L = u_max_phy*dt/dx
u_mean_L = 2.0*u_max_L/3.0

rho0_l = 1.0
cs2_l = 1./3.
cs_inv = 1.0/math.sqrt(cs2_l)
p0_l = rho0_l*cs2_l
press_p = rho0_p*dx^2/dt^2
p0_p = 1e5 --100kPa or 1 atm 

function u_inflow(x,y,z) 
  -- r = math.sqrt(y*y+z*z) -- 3D
  r = y
  u_x = u_max_phy*(1.0 - (r/outer_rad_nozzle)^2.0 )
  return {u_x, 0.0, 0.0}
end

