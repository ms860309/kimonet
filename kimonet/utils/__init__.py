import numpy as np
from kimonet.utils.rotation import rotate_vector


def minimum_distance_vector(r_vector, supercell):
    # lattice periodicity
    r_vector = np.array(r_vector).copy()
    cell_vector = []

    for lattice in supercell:
        half_cell = np.array(lattice) / 2
        dot_ref = np.dot(half_cell, half_cell)
        dot = np.dot(half_cell, r_vector)
        n_n = (np.abs(dot) // dot_ref) * np.sign(dot)
        r_vector += np.array(lattice) * -n_n
        cell_vector.append(-n_n)

    return r_vector, np.array(cell_vector, dtype=int)