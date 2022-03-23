import numpy as np

def fill_none(data, var_names):
    """Fills an array with None values in order to match dimensions for tabulating data."""
    row_lengths = []
    for i in range(len(data)):
        row_lengths.append(len(np.array(data[i])))
    max_l = max(row_lengths)
    #Now compensate shorter rows by appending None so data can be tabulated
    for i in range(len(data)):
        while len(data[i]) < max_l:
            data[i].append([None]*len(var_names))
    return data
