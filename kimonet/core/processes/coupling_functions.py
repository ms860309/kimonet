import numpy as np
from kimonet.utils import minimum_distance_vector
import inspect
from collections import namedtuple
from kimonet.utils.units import VAC_PERMITTIVITY

##########################################################################################
#                                   COUOPLING FUNCTIONS
##########################################################################################

coupling_memory = {}


def compute_forster_coupling(donor, acceptor, conditions, supercell):
    """
    Compute Forster coupling in eV

    :param donor: excited molecules. Donor
    :param acceptor: neighbouring molecule. Possible acceptor
    :param conditions: dictionary with physical conditions
    :param supercell: the supercell of the system
    :return: Forster coupling between both molecules. We don't implement any correction for short distances.
    """

    function_name = inspect.currentframe().f_code.co_name

    # donor <-> acceptor interaction symmetry
    hash_string = str(hash((donor, function_name)) + hash((acceptor, function_name)))
    # hash_string = str(hash((donor, acceptor, function_name))) # No symmetry

    if hash_string in coupling_memory:
        return coupling_memory[hash_string]

    mu_d = donor.get_transition_moment()                     # transition dipole moment (donor) a.u
    mu_a = acceptor.get_transition_moment()                  # transition dipole moment (acceptor) a.u

    r_vector = intermolecular_vector(donor, acceptor)       # position vector between donor and acceptor
    r_vector, _ = minimum_distance_vector(r_vector, supercell)

    r = np.linalg.norm(r_vector)

    n = conditions['refractive_index']                      # refractive index of the material

    k = orientation_factor(mu_d, mu_a, r_vector)              # orientation factor between molecules

    k_e = 1.0/(4.0*np.pi*VAC_PERMITTIVITY)
    forster_coupling = k_e * k**2 * np.dot(mu_d, mu_a) / (n**2 * r**3)

    coupling_memory[hash_string] = forster_coupling                            # memory update for new couplings

    return forster_coupling


##########################################################################################
#                               COUPLING FUNCTIONS DICTIONARY
##########################################################################################
Transfer = namedtuple("Transfer", ["initial", "final", "description"])

# Transfer tuple format:
# initial: tuple with the initial states of donor, acceptor for the transfer to occur (order is important!!)
# final: tuple with the final states of the donor, acceptor once the transfer has occurred
# description: string with some information about the transfer process


functions_dict = {Transfer(initial=('s1', 'gs'), final=('gs', 's1'), description='forster'): compute_forster_coupling}

##########################################################################################
#                            AUXILIARY FUNCTIONS
##########################################################################################


def intermolecular_vector(donor, acceptor):
    """
    :param donor: donor
    :param acceptor: acceptor
    :return: the distance between the donor and the acceptor
    """
    position_d = donor.get_coordinates()
    position_a = acceptor.get_coordinates()
    r = position_a - position_d

    return r


def orientation_factor(u_d, u_a, r):
    """
    :param u_d: dipole transition moment of the donor
    :param u_a: dipole transition moment of the acceptor
    :param r:  intermolecular_distance
    :return: the orientational factor between both molecules
    """
    nd = unit_vector(u_d)
    na = unit_vector(u_a)
    e = unit_vector(r)
    return np.dot(nd, na) - 3*np.dot(e, nd)*np.dot(e, na)


def unit_vector(vector):
    """
    :param vector:
    :return: computes a unity vector in the direction of vector
    """
    return vector / np.linalg.norm(vector)
