from kimonet.core.processes.fcwd import general_fcwd
from kimonet.utils.units import HBAR_PLANCK
import numpy as np
# from kimonet.system.vibrations import NoVibration
from scipy.integrate import quad

overlap_data = {}


class Transition:
    def __init__(self, state1, state2, symmetric=True):
        self._state1 = state1
        self._state2 = state2
        self._symmetric = symmetric

    def __hash__(self):
        if self._symmetric:
            return hash(self._state1) + hash(self._state2)
        else:
            return hash((self._state1, self._state2))

    def __eq__(self, other):
        return hash(self) == hash(other)


class BaseProcess:
    def __init__(self,
                 initial_states,
                 final_states,
                 description='',
                 arguments=None
                 ):

        self.initial = initial_states
        self.final = final_states
        self.description = description
        self.arguments = arguments if arguments is not None else {}
        self._donor = None
        self._acceptor = None
        self._cell_increment = None
        self._supercell = None

    @property
    def donor(self):
        if self._donor is None:
            raise Exception('No donor set')
        return self._donor

    @donor.setter
    def donor(self, molecule):
        assert molecule.state.label == self.initial[0].label
        self._donor = molecule

    @property
    def acceptor(self):
        if self._acceptor is None:
            raise Exception('No acceptor set')
        return self._acceptor

    @acceptor.setter
    def acceptor(self, molecule):
        assert molecule.state.label == self.initial[1].label
        self._acceptor = molecule

    @property
    def cell_increment(self):
        if self._cell_increment is None:
            raise Exception('No cell_increment set')
        return self._cell_increment

    @cell_increment.setter
    def cell_increment(self, cell_incr):
        self._cell_increment = cell_incr


    @property
    def supercell(self):
        if self._supercell is None:
            raise Exception('No supercell')
        return self._supercell

    @supercell.setter
    def supercell(self, cell):
        self._supercell = cell


class GoldenRule(BaseProcess):
    def __init__(self,
                 initial_states,
                 final_states,
                 electronic_coupling_function,
                 description='',
                 arguments=None,
                 ):

        self._coupling_function = electronic_coupling_function
        BaseProcess.__init__(self, initial_states, final_states, description, arguments)

    def get_fcwd(self):
        transition_donor = (self.initial[0], self.final[0])
        transition_acceptor = (self.initial[1], self.final[1])

        donor_vib_dos = self.donor.vibrations.get_vib_spectrum(*transition_donor)  # (transition_donor)
        acceptor_vib_dos = self.acceptor.vibrations.get_vib_spectrum(*transition_acceptor)  # (transition_acceptor)

        # print(donor_vib_dos)
        info = str(hash(donor_vib_dos) + hash(acceptor_vib_dos))

        # the memory is used if the overlap has been already computed
        if info in overlap_data:
            return overlap_data[info]

        def overlap(x):
            return donor_vib_dos(x) * acceptor_vib_dos(x)

        overlap_data[info] = quad(overlap, 0, np.inf, epsabs=1e-5, limit=1000)[0]

        return overlap_data[info]

    def get_electronic_coupling(self, conditions):
        # conditions will be deprecated
        return self._coupling_function(self.donor, self.acceptor, conditions, self.supercell, self.cell_increment, **self.arguments)

    def get_rate_constant(self, conditions, supercell):
        e_coupling = self.get_electronic_coupling(conditions)
        #spectral_overlap = general_fcwd(self.donor, self.acceptor, self, conditions)

        spectral_overlap = self.get_fcwd()

        return 2 * np.pi / HBAR_PLANCK * e_coupling ** 2 * spectral_overlap  # Fermi's Golden Rule


class DirectRate(BaseProcess):
    def __init__(self,
                 initial_states,
                 final_states,
                 rate_constant_function,
                 description='',
                 arguments=None
                 ):

        self.rate_function = rate_constant_function
        BaseProcess.__init__(self, initial_states, final_states, description, arguments)

    def get_rate_constant(self, conditions, supercell):
        return self.rate_function(self.donor, self.acceptor, conditions, self.supercell, self.cell_increment)


class DecayRate(BaseProcess):
    def __init__(self,
                 initial_states,
                 final_states,
                 decay_rate_function,
                 description='',
                 arguments=None
                 ):

        BaseProcess.__init__(self, [initial_states], [final_states], description, arguments)
        self.rate_function = decay_rate_function

    def get_rate_constant(self, *args):
        return self.rate_function(self.initial, self.final, self.donor, **self.arguments)
