# This works only in python 3
from kimonet.system.generators import regular_system
from kimonet.analysis import Trajectory, visualize_system, TrajectoryAnalysis
from kimonet import system_test_info
from kimonet.system.molecule import Molecule
from kimonet.system.state import State
from kimonet import do_simulation_step
from kimonet.core.processes.couplings import forster_coupling
from kimonet.core.processes.decays import einstein_radiative_decay
from kimonet.core.processes import GoldenRule, DecayRate, DirectRate
from kimonet.system.vibrations import MarcusModel, LevichJortnerModel, EmpiricalModel
import concurrent.futures as futures


transfer_scheme = [GoldenRule(initial=('s1', 'gs'), final=('gs', 's1'),
                              electronic_coupling_function=forster_coupling,
                              description='forster')
                   ]

decay_scheme = [DecayRate(initial='s1', final='gs',
                          decay_rate_function=einstein_radiative_decay,
                          description='singlet_radiative_decay')
                ]


molecule = Molecule(states=[State(label='gs', energy=0.0),  # eV
                            State(label='s1', energy=1.0)], # eV
                    vibrations=MarcusModel(reorganization_energies={('s1', 'gs'): 0.5,    # eV
                                                                    ('gs', 's1'): 0.5}),  # eV
                    transition_moment={('s1', 'gs'): [1.0, 0]},  # transition dipole moment of the molecule (Debye)
                    decays=decay_scheme
                    )

#######################################################################################################################

# physical conditions of the system (as a dictionary)
conditions = {'refractive_index': 1}             # maximum interaction distance (Angstroms)

#######################################################################################################################

num_trajectories = 500                          # number of trajectories that will be simulated
max_steps = 100                              # maximum number of steps for trajectory allowed

system = regular_system(conditions=conditions,
                        molecule=molecule,
                        lattice={'size': [3, 3],
                                 'parameters': [3.0, 3.0]},  # Angstroms
                        orientation=[0, 0, 0])

visualize_system(system)
system.cutoff_radius = 4.0  # Angstroms

system.transfer_scheme = transfer_scheme

system.add_excitation_center('s1')
system_test_info(system)


def run_trajectory(system, index):

    system = system.copy()
    system.add_excitation_center('s1')

    trajectory = Trajectory(system)
    for i in range(max_steps):

        change_step, step_time = do_simulation_step(system)

        if system.is_finished:
            break

        trajectory.add_step(change_step, step_time)

    print('trajectory {} done!'.format(index))
    return trajectory

# executor = futures.ThreadPoolExecutor(max_workers=4)
executor = futures.ProcessPoolExecutor(max_workers=10)

futures_list = []
for i in range(num_trajectories):
    futures_list.append(executor.submit(run_trajectory, system, i))

trajectories = []
for f in futures.as_completed(futures_list):
    trajectories.append(f.result())


analysis = TrajectoryAnalysis(trajectories)

print('diffusion coefficient (average): {} angs^2/ns'.format(analysis.diffusion_coefficient('s1')))
print('lifetime: {} ns'.format(analysis.lifetime('s1')))
print('diffusion length: {} angs'.format(analysis.diffusion_length('s1')))

print('diffusion tensor')
print(analysis.diffusion_coeff_tensor('s1'))
print('diffusion length tensor')
print(analysis.diffusion_length_square_tensor('s1'))
# print(np.sqrt(analysis.diffusion_coeff_tensor()*analysis.lifetime()*2))

plt = analysis.plot_2d()
plt.figure()
analysis.plot_distances()
plt.show()
