# from kimonet.core.processes import Transfer
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from scipy import stats
import warnings
import os
from copy import deepcopy
from kimonet import _ground_state_


def count_keys_dict(dictionary, key):
    if key in dictionary:
        dictionary[key] += 1
    else:
        dictionary[key] = 1

class ArrayHandler():
    def __init__(self, arraystructure, data):
        self.arraystructure = arraystructure

        if data in self.arraystructure.dtype.fields:
            self.data = data
        else:
            raise Exception('Data not in array')

        # determine data position
        for i, element in enumerate(self.arraystructure.dtype.fields):
            if self.data == element:
                self.index = i

        # set initial data len
        self.data_len = len(arraystructure)

    def __str__(self):
        return str(self.arraystructure[self.data][:self.data_len])

    def __getitem__(self, item):
        return self.arraystructure[self.data][:self.data_len][item]

    def __len__(self):
        return self.data_len

    def append(self, value):

        if self.data_len >= len(self.arraystructure):
            self.arraystructure.resize((len(self.arraystructure) + 1,), refcheck=False)
            new_element = [None] * len(self.arraystructure.dtype.fields)
        else:
            new_element = list(self.arraystructure[self.data_len])

        new_element[self.index] = deepcopy(value)
        self.arraystructure[self.data_len] = tuple(new_element)
        self.data_len += 1


class TrajectoryGraph:
    def __init__(self, system):
        """
        Stores and analyzes the information of a kinetic MC trajectory
        system: system
        """

        self.node_count = len(system.centers)

        self.graph = nx.DiGraph()

        for i, center in enumerate(system.centers):
            self.graph.add_node(i,
                                coordinates=[list(system.molecules[center].get_coordinates())],
                                state=system.molecules[center].state.label,
                                cell_state=[list(system.molecules[center].cell_state)],
                                time=[0],
                                event_time=0,
                                index=[center],
                                finished=False,
                                )

        self.supercell = np.array(system.supercell)
        self.system = system

        self.n_dim = len(system.molecules[0].get_coordinates())
        self.n_centers = len(system.centers)
        self.labels = {}
        self.times = [0]

        self.states = set()
        ce = {}
        for center in system.centers:
            state = system.molecules[center].state.label
            self.states.add(state)
            count_keys_dict(ce, state)
        self.current_excitons = [ce]

    def _finish_node(self, inode):

        node = self.graph.nodes[inode]
        if not node['finished']:
            # index = change_step['donor']
            node['index'].append(node['index'][-1])
            node['coordinates'].append(node['coordinates'][-1])
            node['time'].append(self.times[-1] - node['event_time'])
            node['cell_state'].append(node['cell_state'][-1])
            node['finished'] = True

    def _add_node(self, from_node, new_on_molecule, process_label=None):

        if self.system.molecules[new_on_molecule].set_state(_ground_state_):
            print('Error in state: ', self.system.molecules[new_on_molecule].state.label)
            exit()

        self.graph.add_edge(from_node, self.node_count, process_label=process_label)
        self.graph.add_node(self.node_count,
                            coordinates=[list(self.system.molecules[new_on_molecule].get_coordinates())],
                            state=self.system.molecules[new_on_molecule].state.label,
                            cell_state=[list(self.system.molecules[new_on_molecule].cell_state)],
                            # cell_state=[[0, 0]],
                            time=[0],
                            event_time=self.times[-1],
                            index=[new_on_molecule],
                            finished=False
                            )
        self.node_count += 1

    def _append_to_node(self, on_node, add_molecule):
        node = self.graph.nodes[on_node]

        node['index'].append(add_molecule)
        node['coordinates'].append(list(self.system.molecules[add_molecule].get_coordinates()))
        node['cell_state'].append(list(self.system.molecules[add_molecule].cell_state))
        node['time'].append(self.times[-1] - node['event_time'])

    def add_step(self, change_step, time_step):
        """
        Adds trajectory step

        :param change_step: process occurred during time_step: {donor, process, acceptor}
        :param time_step: duration of the chosen process
        """
        # print(change_step)
        # print(self.system.molecules[change_step['donor']].get_coordinates(), self.system.molecules[change_step['acceptor']].get_coordinates())
        # print(self.system.molecules[change_step['donor']].cell_state, self.system.molecules[change_step['acceptor']].cell_state)

        self.times.append(self.times[-1] + time_step)

        end_points = [node for node in self.graph.nodes
                      if len(list(self.graph.successors(node))) == 0 and not self.graph.nodes[node]['finished']]

        node_link = {'donor': None, 'acceptor': None}
        for inode in end_points:
            node = self.graph.nodes[inode]
            if node['index'][-1] == change_step['donor']:
                node_link['donor'] = inode
            if node['index'][-1] == change_step['acceptor']:
                node_link['acceptor'] = inode

        process = change_step['process']

        if change_step['donor'] == change_step['acceptor']:
            # Intramolecular conversion
            self._finish_node(node_link['donor'])

            # Check if not ground state
            final_state = self.system.molecules[change_step['acceptor']].state.label
            if final_state != _ground_state_:
                self._add_node(from_node=node_link['donor'],
                               new_on_molecule=change_step['acceptor'],
                               process_label=process.description)

        else:
            # Intermolecular process
            if (process.initial[0] == process.final[1]
                    and process.final[1] != _ground_state_
                    and process.final[0] == _ground_state_):
                # s1, X  -> X, s1
                # Simple transfer
                # print('C1')
                self._append_to_node(on_node=node_link['donor'],
                                     add_molecule=change_step['acceptor'])

            elif (process.initial[0] != process.final[1]
                    and process.initial[0] != _ground_state_ and process.final[1] != _ground_state_
                    and process.final[0] == _ground_state_ and process.initial[1] == _ground_state_):
                # s1, X  -> X, s2
                # Transfer with change
                # print('C2')
                self._finish_node(node_link['donor'])

                self._add_node(from_node=node_link['donor'],
                               new_on_molecule=change_step['acceptor'],
                               process_label=process.description)

            elif (process.initial[0] != process.final[0] and process.initial[0] != process.final[1]
                    and process.initial[0] != _ground_state_
                    and process.final[0] != _ground_state_
                    and process.final[1] != _ground_state_
                    and process.initial[1] == _ground_state_):
                # s1, X  -> s2, s3
                # Exciton splitting
                # print('C3')
                self._finish_node(node_link['donor'])

                self._add_node(from_node=node_link['donor'],
                               new_on_molecule=change_step['donor'],
                               process_label=process.description)

                self._add_node(from_node=node_link['donor'],
                               new_on_molecule=change_step['acceptor'],
                               process_label=process.description)

            elif (process.initial[0] != process.final[1] and process.initial[1] != process.final[1]
                    and process.initial[0] != _ground_state_
                    and process.initial[1] != _ground_state_
                    and process.final[0] == _ground_state_
                    and process.final[1] != _ground_state_):
                # s1, s2  ->  X, s3
                # Exciton merge type 1
                # print('C4')
                self._finish_node(node_link['donor'])
                self._finish_node(node_link['acceptor'])

                self._add_node(from_node=node_link['donor'],
                               new_on_molecule=change_step['acceptor'],
                               process_label=process.description)

                self.graph.add_edge(node_link['acceptor'], self.node_count-1, process_label=process.description)

            elif (process.initial[0] != process.final[0] and process.initial[1] != process.final[0]
                    and process.initial[0] != _ground_state_
                    and process.initial[1] != _ground_state_
                    and process.final[0] != _ground_state_
                    and process.final[1] == _ground_state_):
                # s1, s2  ->  s3, X
                # Exciton merge type 2
                # print('C5')
                self._finish_node(node_link['donor'])
                self._finish_node(node_link['acceptor'])

                self._add_node(from_node=node_link['donor'],
                               new_on_molecule=change_step['donor'],
                               process_label=process.description)

                self.graph.add_edge(node_link['acceptor'], self.node_count-1, process_label=process.description)

            elif (process.initial[0] != process.final[0] and process.initial[1] != process.final[1]
                  and process.initial[0] == process.final[1] and process.initial[0] == process.final[1]
                  and process.initial[0] != _ground_state_
                  and process.initial[1] != _ground_state_
                  and process.final[0] != _ground_state_
                  and process.final[1] != _ground_state_):
                # s1, s2  ->  s2, s1
                # Exciton cross interaction (treated as double transport)
                # print('C6')

                self._append_to_node(on_node=node_link['donor'],
                                     add_molecule=change_step['acceptor'])

                self._append_to_node(on_node=node_link['acceptor'],
                                     add_molecule=change_step['donor'])

            elif (process.initial[0] != process.final[0] and process.initial[1] != process.final[1]
                  and process.initial[0] != process.final[1] and process.initial[0] != process.final[1]
                  and process.initial[0] != _ground_state_
                  and process.initial[1] != _ground_state_
                  and process.final[0] != _ground_state_
                  and process.final[1] != _ground_state_):
                # s1, s2  ->  s3, s4
                # Exciton double evolution
                print('C7')
                self._finish_node(node_link['donor'])
                self._finish_node(node_link['acceptor'])

                self._add_node(from_node=node_link['donor'],
                               new_on_molecule=change_step['acceptor'],
                               process_label=process.description)

                self._add_node(from_node=node_link['acceptor'],
                               new_on_molecule=change_step['donor'],
                               process_label=process.description)

                self.graph.add_edge(node_link['acceptor'], self.node_count-2, process_label=process.description)
                self.graph.add_edge(node_link['donor'], self.node_count-1, process_label=process.description)
            else:
                raise Exception('Error: No process type found')

        ce = {}
        for center in self.system.centers:
            state = self.system.molecules[center].state.label
            self.states.add(state)
            count_keys_dict(ce, state)

        self.current_excitons.append(ce)
        # print('add_step_out:', self.graph.nodes[node_link['donor']]['cell_state'][-5:], len(self.graph.nodes[node_link['donor']]['cell_state']))

    def plot_graph(self):

        # cmap = cm.get_cmap('Spectral')
        # default matplotlib color cycle list
        color_list = [u'#1f77b4', u'#ff7f0e', u'#2ca02c', u'#d62728', u'#9467bd', u'#8c564b', u'#e377c2', u'#7f7f7f', u'#bcbd22', u'#17becf']

        colors_map = {}
        node_map = {}
        for i, state in enumerate(self.get_states()):
            colors_map[state] = np.roll(color_list, -i)[0]
            node_map[state] = []

        for node in self.graph:
            state = self.graph.nodes[node]['state']
            node_map[state].append(node)

        #pos = nx.spring_layout(self.graph)
        pos = nx.drawing.nx_agraph.graphviz_layout(self.graph, prog='dot')
        for state in self.get_states():
            nx.draw_networkx_nodes(self.graph,
                                   pos=pos,
                                   nodelist=node_map[state],
                                   node_color=colors_map[state],
                                   label=state)
        nx.draw_networkx_edges(self.graph, pos=pos)
        nx.draw_networkx_labels(self.graph, pos=pos)
        plt.legend()

        return plt

    def get_states(self):
        return self.states

    def get_dimension(self):
        return self.n_dim

    def get_graph(self):
        return self.graph

    def get_times(self):
        return self.times

    def _vector_list(self, state):
        node_list = [node for node in self.graph.nodes if self.graph.nodes[node]['state'] == state]

        vector = []
        t = []
        for node in node_list:
            t += self.graph.nodes[node]['time']
            # print('node**', node)

            initial = np.array(self.graph.nodes[node]['coordinates'][0])
            cell_state_i = self.graph.nodes[node]['cell_state'][0]

            # print('cell**', self.G.nodes[node]['cell_state'], len(self.G.nodes[node]['cell_state']))
            for coordinate, cell_state in zip(self.graph.nodes[node]['coordinates'], self.graph.nodes[node]['cell_state']):
                lattice = np.dot(self.supercell.T, cell_state) - np.dot(self.supercell.T, cell_state_i)
                vector.append(np.array(coordinate) - lattice - initial)

        vector = np.array(vector).T
        return vector, t

    def get_diffusion(self, state):

        vector, t = self._vector_list(state)

        if not np.array(t).any():
            return 0

        n_dim, n_length = vector.shape

        vector2 = np.linalg.norm(vector, axis=0)**2  # emulate dot product in axis 0

        # plt.plot(t, vector2, 'o')
        # plt.show()
        with np.errstate(invalid='ignore'):
            slope, intercept, r_value, p_value, std_err = stats.linregress(t, vector2)

        return slope/(2*n_dim)

    def get_diffusion_tensor(self, state):

        vector, t = self._vector_list(state)

        if not np.array(t).any():
            return np.zeros((self.n_dim, self.n_dim))

        tensor_x = []
        for v1 in vector:
            tensor_y = []
            for v2 in vector:
                vector2 = v1*v2
                with np.errstate(invalid='ignore'):
                    slope, intercept, r_value, p_value, std_err = stats.linregress(t, vector2)
                tensor_y.append(slope)
            tensor_x.append(tensor_y)

        return np.array(tensor_x)/2

    def get_number_of_cumulative_excitons(self, state=None):
        time = []
        node_count = []
        print('This is wrong!!, accumulated')
        for node in self.graph.nodes:
            time.append(self.graph.nodes[node]['event_time'])
            if state is not None:
                if self.graph.nodes[node]['event_time'] == state:
                    node_count.append(node_count[-1]+1)
            else:
                node_count.append(node)
        return time, node_count

    def get_number_of_excitons(self, state=None):
        excitations_count = []
        for t, status in zip(self.times, self.current_excitons):
            if state is None:
                excitations_count.append(np.sum(list(status.values())))
            else:
                if state in status:
                    excitations_count.append(status[state])
                else:
                    excitations_count.append(0)

        return excitations_count

    def plot_number_of_cumulative_excitons(self, state=None):
        t, n = self.get_number_of_cumulative_excitons(state)
        plt.plot(t, n, '-o')
        return plt

    def plot_number_of_excitons(self, state=None):
        n = self.get_number_of_excitons(state)
        plt.plot(self.times, n, '-o')
        return plt


    def get_number_of_nodes(self):
        return self.graph.number_of_nodes()

    def plot_2d(self, state=None, supercell_only=False):

        if state is None:
            node_list = [node for node in self.graph.nodes]
        else:
            node_list = [node for node in self.graph.nodes if self.graph.nodes[node]['state'] == state]

        t = []
        coordinates = []
        for node in node_list:
            t += [self.graph.nodes[node]['time'] for node in node_list]

            if supercell_only:
                coordinates += [self.graph.nodes[node]['coordinates'] for node in node_list]

            else:
                vector = []
                initial = self.graph.nodes[node]['coordinates'][0]
                for cell_state, coordinate in zip(self.graph.nodes[node]['cell_state'], self.graph.nodes[node]['coordinates']):
                    lattice = np.dot(self.supercell.T, cell_state)
                    vector.append(np.array(coordinate) - lattice)
                    # print(lattice)
                coordinates += vector
                # print(vector)
                plt.plot(np.array(vector).T[0], np.array(vector).T[1], '-o')
                # plt.show()

        if self.get_dimension() != 2:
            raise Exception('plot_2d can only be used in 2D systems')

        coordinates = np.array(coordinates).T

        if len(coordinates) == 0:
            # warnings.warn('No data for state {}'.format(state))
            return plt

        # plt.plot(coordinates[0], coordinates[1], '-o')
        plt.title('exciton trajectories ({})'.format(state))

        return plt

    def get_distances_vs_times(self, state=None):

        if state is None:
            node_list = [node for node in self.graph.nodes]
        else:
            node_list = [node for node in self.graph.nodes if self.graph.nodes[node]['state'] == state]

        t = []
        coordinates = []
        for node in node_list:
            t += self.graph.nodes[node]['time']

            vector = []
            initial = self.graph.nodes[node]['coordinates'][0]
            cell_state_i = self.graph.nodes[node]['cell_state'][0]

            for cell_state, coordinate in zip(self.graph.nodes[node]['cell_state'], self.graph.nodes[node]['coordinates']):
                lattice = np.dot(self.supercell.T, cell_state) - np.dot(self.supercell.T, cell_state_i)
                vector.append(np.array(coordinate) - lattice - initial)
                # print('lattice: ', lattice)

            # print('->', [np.linalg.norm(v, axis=0) for v in vector])
            # print('->', t)
            # plt.plot(self.graph.nodes[node]['time'], [np.linalg.norm(v, axis=0) for v in vector], '-o')

            coordinates += vector

        vector = np.array(coordinates).T

        if len(coordinates) == 0:
            # warnings.warn('No data for state {}'.format(state))
            return [], []

        vector = np.linalg.norm(vector, axis=0)

        return vector, t

    def get_max_distances_vs_times(self, state):

        if state is None:
            node_list = [node for node in self.graph.nodes]
        else:
            node_list = [node for node in self.graph.nodes if self.graph.nodes[node]['state'] == state]

        t = []
        coordinates = []
        for node in node_list:
            t += self.graph.nodes[node]['time']

            vector = []
            initial = np.array(self.graph.nodes[node]['coordinates'][0])
            cell_state_i = self.graph.nodes[node]['cell_state'][0]
            final = np.array(self.graph.nodes[node]['coordinates'][-1])
            cell_state_f = self.graph.nodes[node]['cell_state'][-1]

            lattice = np.dot(self.supercell.T, cell_state_f) - np.dot(self.supercell.T, cell_state_i)
            vector.append(final - lattice - initial)

            coordinates += vector

        vector = np.array(coordinates).T

        if len(coordinates) == 0:
            # warnings.warn('No data for state {}'.format(state))
            return [], []

        vector = np.linalg.norm(vector, axis=0)

        return vector, t

    def plot_distances(self, state=None):

        vector, t = self.get_distances_vs_times(state)

        # print(t)
        plt.title('diffusion distances ({})'.format(state))
        plt.plot(t, vector, '.')
        plt.xlabel('Time (ns)')
        plt.ylabel('Distance (Angs)')

        return plt

    def get_lifetime(self, state):

        node_list = [node for node in self.graph.nodes if self.graph.nodes[node]['state'] == state]

        if len(node_list) == 0:
            return 0

        t = [self.graph.nodes[node]['time'][-1] for node in node_list]

        return np.average(t)

    def get_lifetime_ratio(self, state):

        t_tot = self.times[-1]

        return self.get_lifetime(state)/t_tot

    def get_diffusion_length_square(self, state):

        node_list = [node for node in self.graph.nodes if self.graph.nodes[node]['state'] == state]

        dot_list = []
        for node in node_list:
            # print('node', node)


            coordinates_i = np.array(self.graph.nodes[node]['coordinates'][0])
            cell_state_i = np.array(self.graph.nodes[node]['cell_state'][0])

            coordinates_f = np.array(self.graph.nodes[node]['coordinates'][-1])
            cell_state_f = np.array(self.graph.nodes[node]['cell_state'][-1])

            # print('cell', cell_state_f, cell_state_i)
            lattice_diff = np.dot(self.supercell.T, cell_state_f) - np.dot(self.supercell.T, cell_state_i)

            vector = coordinates_f - lattice_diff - coordinates_i

            dot_list.append(np.dot(vector, vector))

        if len(dot_list) == 0:
            return np.nan

        # print(dot_list)
        # exit()
        return np.average(dot_list)

    def get_diffusion_length_square_tensor(self, state):

        node_list = [node for node in self.graph.nodes if self.graph.nodes[node]['state'] == state]

        distances = []
        for node in node_list:
            coordinates_i = np.array(self.graph.nodes[node]['coordinates'][0])
            cell_state_i = np.array(self.graph.nodes[node]['cell_state'][0])

            coordinates_f = np.array(self.graph.nodes[node]['coordinates'][-1])
            cell_state_f = np.array(self.graph.nodes[node]['cell_state'][-1])

            lattice_diff = np.dot(self.supercell.T, cell_state_f) - np.dot(self.supercell.T, cell_state_i)

            vector = coordinates_f - lattice_diff - coordinates_i

            distances.append(vector)

        tensor = []
        for vector in distances:
            tensor_x = []
            for v1 in vector:
                tensor_y = []
                for v2 in vector:
                    tensor_y.append(v1*v2)
                tensor_x.append(tensor_y)

            tensor.append(np.array(tensor_x))

        # If no data for this state in this particular trajectory return nan matrix
        if len(tensor) == 0:
            return np.nan

        return np.average(tensor, axis=0)


class TrajectoryGraph2(TrajectoryGraph):
    def __init__(self, system):
        """
        Stores and analyzes the information of a kinetic MC trajectory
        system: system
        """

        self.node_count = len(system.centers)

        self.graph = nx.DiGraph()

        if not os.path.exists('test_map'):
            os.mkdir('test_map')

        self.mapped_list = []
        for i, center in enumerate(system.centers):

            mem_array = np.require(np.memmap('test_map/array_{}_{}_{}'.format(id(self), os.getpid(), i),
                                             dtype=[('coordinates', object),
                                                    ('cell_state', object),
                                                    ('time', object),
                                                    ('index', object)],
                                             mode='w+', shape=(1,)),
                                   requirements=['O'])

            mem_array[:] = (system.molecules[center].get_coordinates(),
                            system.molecules[center].cell_state,
                            0.0,
                            center)

            self.graph.add_node(i,
                                coordinates=ArrayHandler(mem_array, 'coordinates'),
                                state=system.molecules[center].state.label,
                                cell_state=ArrayHandler(mem_array, 'cell_state'),
                                time=ArrayHandler(mem_array, 'time'),
                                event_time=0,
                                index=ArrayHandler(mem_array, 'index'),
                                finished=False,
                                )
            self.mapped_list.append((mem_array, 'test_map/array_{}_{}_{}'.format(id(self), os.getpid(), i)))

        self.supercell = system.supercell
        self.system = system

        self.n_dim = len(system.molecules[0].get_coordinates())
        self.n_centers = len(system.centers)
        self.labels = {}

        mem_array_t = np.require(np.memmap('test_map/array_{}_{}_{}'.format(id(self), os.getpid(), 't'),
                                           dtype=[('times', object)],
                                           mode='w+', shape=(1,)),
                                 requirements=['O'])

        mem_array_t[:] = (0)
        self.times = ArrayHandler(mem_array_t, 'times')
        self.mapped_list.append((mem_array_t, 'test_map/array_{}_{}_{}'.format(id(self), os.getpid(),'t')))

        self.states = set()
        ce = {}
        for center in system.centers:
            state = system.molecules[center].state.label
            self.states.add(state)
            count_keys_dict(ce, state)
        self.current_excitons = [ce]

    def _add_node(self, from_node, new_on_molecule, process_label=None):

        if self.system.molecules[new_on_molecule].set_state(_ground_state_):
            print('Error in state: ', self.system.molecules[new_on_molecule].state.label)
            exit()

        mem_array = np.require(np.memmap('test_map/array_{}_{}_{}'.format(id(self), os.getpid(), self.node_count),
                                         dtype=[('coordinates', object),
                                                ('cell_state', object),
                                                ('time', object),
                                                ('index', object)],
                                         mode='w+', shape=(1,)),
                               requirements=['O'])

        mem_array[:] = (self.system.molecules[new_on_molecule].get_coordinates(),
                        self.system.molecules[new_on_molecule].cell_state,
                        0.0,
                        new_on_molecule)

        self.graph.add_edge(from_node, self.node_count, process_label=process_label)
        self.graph.add_node(self.node_count,
                            coordinates=ArrayHandler(mem_array, 'coordinates'),
                            state=self.system.molecules[new_on_molecule].state.label,
                            cell_state=ArrayHandler(mem_array, 'cell_state'),
                            time=ArrayHandler(mem_array, 'time'),
                            event_time=self.times[-1],
                            index=ArrayHandler(mem_array, 'index'),
                            finished=False
                            )

        self.mapped_list.append((mem_array, 'test_map/array_{}_{}_{}'.format(id(self), os.getpid(), self.node_count)))

        self.node_count += 1

    def __del__(self):
        for mapped_array, filename in self.mapped_list:
            del mapped_array
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass
