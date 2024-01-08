 format = 'asciispatial'
 solver = 'Musubi_v1.1'
 simname = 'nozzle'
 basename = 'tracking/nozzle_2D_hline'
 glob_rank = 0
 glob_nprocs = 4
 sub_rank = 0
 sub_nprocs = 4
 resultfile = 'tracking/nozzle_2D_hline_p*'
 nDofs = 1
 nElems = 319
 time_control = {
    min = {
        iter = 0 
    },
    max = {
        iter = 44416 
    },
    interval = {
        iter = 1110 
    },
    check_iter = 1 
}
 shape = {
    {
        canonicalND = {
            {
                origin = { -100.000000000000006E-03,    0.000000000000000E+00,  312.500000000000007E-06 },
                vec = {
                    {  200.000000000000011E-03,    0.000000000000000E+00,    0.000000000000000E+00 } 
                },
                segments = {
                    320 
                },
                distribution = 'equal' 
            } 
        } 
    } 
}
 varsys = {
    systemname = '2D',
    variable = {
        {
            name = 'normalized_pressure',
            ncomponents = 1 
        },
        {
            name = 'velocity_phy',
            ncomponents = 3 
        } 
    },
    nScalars = 4,
    nStateVars = 2 
}
