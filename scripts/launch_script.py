from kimonet.system.generators import regular_system, crystal_system
from kimonet.analysis import Trajectory, visualize_system, TrajectoryAnalysis
from kimonet.system.molecule import Molecule
from kimonet import do_simulation_step
from kimonet.core.processes.couplings import forster_coupling, dexter_coupling
from kimonet.core.processes.decays import einstein_singlet_decay
from kimonet.core.processes import Transfer, Decay
import kimonet.core.processes as processes

import numpy as np
np.random.seed(1)  # for testing


processes.transfer_scheme = {Transfer(initial=('s1', 'gs'), final=('gs', 's1'), description='Forster'): forster_coupling,
                             # Transfer(initial=('t1', 'gs'), final=('gs', 't1'), description='Dexter'): dexter_coupling,
                             # Transfer(initial=('s1', 'gs'), final=('gs', 's2'), description='test2'): dexter_coupling,
                             # Transfer(initial=('s2', 'gs'), final=('gs', 's2'), description='test3'): forster_coupling,
                             # Transfer(initial=('s2', 'gs'), final=('gs', 's1'), description='test3'): dexter_coupling
                             }

decay_scheme = {Decay(initial='s1', final='gs', description='singlet_radiative_decay'): einstein_singlet_decay,
                Decay(initial='s1', final='s2', description='test1'): einstein_singlet_decay,
                Decay(initial='s2', final='gs', description='test2'): einstein_singlet_decay,
                }

# excitation energies of the electronic states (eV)
state_energies = {'gs': 0,
                  's1': 1,
                  's2': 1}

# reorganization energies of the states (eV)
reorganization_energies = {'gs': 0,
                           's1': 0.2,
                           's2': 0.2}

molecule = Molecule(state_energies=state_energies,
                    reorganization_energies=reorganization_energies,
                    transition_moment=[2.0, 0],  # transition dipole moment of the molecule (Debye)
                    decays=decay_scheme,
                    vdw_radius=1.7
                    )

#######################################################################################################################

# physical conditions of the system (as a dictionary)
conditions = {'temperature': 273.15,            # temperature of the system (K)
              'refractive_index': 1,            # refractive index of the material (adimensional)
              'cutoff_radius': 3.1,             # maximum interaction distance (Angstroms)
              'dexter_k': 1.0}                  # eV

#######################################################################################################################

num_trajectories = 50                          # number of trajectories that will be simulated
max_steps = 100000                              # maximum number of steps for trajectory allowed

system_1 = regular_system(conditions=conditions,
                          molecule=molecule,
                          lattice={'size': [3, 3], 'parameters': [3.0, 3.0]},  # Angstroms
                          orientation=[0, 0, 0])  # (Rx, Ry, Rz) if None then random orientation


system_2 = crystal_system(conditions=conditions,
                          molecule=molecule,
                          scaled_coordinates=[[0, 0],
                                              [1, 1]],
                          unitcell=[[2.0, 0.5],
                                    [0.0, 2.0]],
                          dimensions=[3, 3],
                          orientations=[[0, 0, np.pi/2],  # if element is None then random, if list then oriented
                                      None])


system = system_1  # choose 1

visualize_system(system)

trajectories = []
for j in range(num_trajectories):

    system.add_excitation_center('s1')
    # system.add_excitation_index('s1', 0)
    system.add_excitation_random('s1', 3)

    # visualize_system(system)

    print('iteration: ', j)
    trajectory = Trajectory(system)

    for i in range(max_steps):

        change_step, step_time = do_simulation_step(system)

        if system.is_finished:
            break

        trajectory.add(change_step, step_time)

        # visualize_system(system)

        if i == max_steps-1:
            print('Maximum number of steps reached!!')

    system.reset()

    #print(trajectory.get_lifetime_ratio('s1'), trajectory.get_lifetime_ratio('s2'), trajectory.get_lifetime_ratio('s3'))
    #print(trajectory.get_lifetime_ratio('s3'), trajectory.get_lifetime_ratio('s1') + trajectory.get_lifetime_ratio('s2'))
    #print('---')
    #print(trajectoryg.get_lifetime('s3'))
    #print(trajectoryg.get_lifetime_ratio('s1'), trajectoryg.get_lifetime_ratio('s2'), trajectoryg.get_lifetime_ratio('s3'))
    #print(trajectoryg.get_lifetime_ratio('s3'), trajectoryg.get_lifetime_ratio('s1') + trajectoryg.get_lifetime_ratio('s2'))
    #print('***')

    # plt = trajectory.plot_distances('s1')
    # plt.show()

    trajectories.append(trajectory)

    #print('diff: ', trajectory.get_diffusion('s1'))
    #print('diffT: ', trajectory.get_diffusion_tensor('s1'))
    #print('diffTg: ', trajectoryg.get_diffusion_tensor('s1'))

    #print('lengh: ', trajectory.get_diffusion_length_square('s1'))
    #print('lT: \n', trajectory.get_diffusion_length_square_tensor('s1'))

    #exit()


    import networkx as nx
    import matplotlib.pyplot as plt
    # nx.draw_spring(trajectory.G, with_labels=True)
    #plt.show()
    # exit()

# diffusion properties
analysis = TrajectoryAnalysis(trajectories)

print(analysis)

print('diffusion coefficient (s1): {} angs^2/ns'.format(analysis.diffusion_coefficient('s1')))
print('lifetime: {} ns'.format(analysis.lifetime('s1')))
print('diffusion length: {} angs'.format(analysis.diffusion_length('s1')))
print('diffusion tensor')
print(analysis.diffusion_coeff_tensor('s1'))
print('diffusion length tensor')
print(analysis.diffusion_length_tensor('s1'))
# print(np.sqrt(analysis.diffusion_coeff_tensor()*analysis.lifetime()*2))


plt = analysis.plot_2d('s1')
plt.figure()
analysis.plot_distances('s1')

plt.show()
