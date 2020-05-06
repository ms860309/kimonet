from kimonet.system.generators import regular_system, crystal_system
from kimonet.analysis import visualize_system, TrajectoryAnalysis
from kimonet.system.molecule import Molecule
from kimonet import system_test_info
from kimonet.core.processes.couplings import forster_coupling, dexter_coupling, forster_coupling_extended
from kimonet.core.processes.decays import einstein_singlet_decay
from kimonet.core.processes import GoldenRule, DecayRate, DirectRate
from kimonet.system.vibrations import MarcusModel, LevichJortnerModel, EmpiricalModel
from kimonet.fileio import store_trajectory_list, load_trajectory_list
from kimonet.analysis.diffusion.diffusion_plots import plot_polar_plot
from kimonet import calculate_kmc, calculate_kmc_parallel

import numpy as np

# list of transfer functions by state
transfer_scheme = {
    GoldenRule(initial=('s1', 'gs'), final=('gs', 's1'), description='Forster'): forster_coupling,
}

# list of decay functions by state
decay_scheme = {
    DecayRate(initial='s1', final='gs', description='singlet_radiative_decay'): einstein_singlet_decay,
}

molecule = Molecule(state_energies={'gs': 0,
                                    's1': 4.0},  # eV
                    vibrations=MarcusModel(reorganization_energies={('s1', 'gs'): 0.08,  # eV
                                                                    ('gs', 's1'): 0.08}),
                    transition_moment={('s1', 'gs'): [0.1, 0.0]},  # Debye
                    decays=decay_scheme,
                    )


# physical conditions of the system
conditions = {'temperature': 300,          # temperature of the system (K)
              'refractive_index': 1
              }

# define system as a crystal
system = crystal_system(conditions=conditions,
                        molecule=molecule,  # molecule to use as reference
                        scaled_coordinates=[[0.0, 0.0]],
                        unitcell=[[5.0, 0.0],
                                  [0.0, 5.0]],
                        dimensions=[4, 4],  # supercell size
                        orientations=[[0.0, 0.0, np.pi/2]])  # if element is None then random, if list then Rx Ry Rz

# set initial exciton
system.add_excitation_center('s1')

# set additional system parameters
system.transfer_scheme = transfer_scheme
system.cutoff_radius = 7.0  # interaction cutoff radius in Angstrom

# some system analyze functions
system_test_info(system)
visualize_system(system)
visualize_system(system, dipole='s1')

# do the kinetic Monte Carlo simulation
trajectories = calculate_kmc_parallel(system,
                             num_trajectories=50,    # number of trajectories that will be simulated
                             max_steps=100000,         # maximum number of steps for trajectory allowed
                             silent=False)

# resulting trajectories analysis
analysis = TrajectoryAnalysis(trajectories)

for state in analysis.get_states():
    print('\nState: {}\n--------------------------------'.format(state))
    print('diffusion coefficient: {:9.5e} Angs^2/ns'.format(analysis.diffusion_coefficient(state)))
    print('lifetime:              {:9.5e} ns'.format(analysis.lifetime(state)))
    print('diffusion length:      {:9.5e} Angs'.format(analysis.diffusion_length(state)))
    print('diffusion tensor (angs^2/ns)')
    print(analysis.diffusion_coeff_tensor(state))

    print('diffusion length tensor (Angs)')
    print(analysis.diffusion_length_square_tensor(state))

    plot_polar_plot(analysis.diffusion_coeff_tensor(state),
                    title='Diffusion', plane=[0, 1])

    plot_polar_plot(analysis.diffusion_length_square_tensor(state),
                    title='Diffusion length square', crystal_labels=True, plane=[0, 1])


analysis.plot_excitations('s1').show()
analysis.plot_2d('s1').show()
analysis.plot_distances('s1').show()
analysis.plot_histogram('s1').show()
analysis.plot_histogram('s1').savefig('histogram_s1.png')

store_trajectory_list(trajectories, 'example_simple.h5')