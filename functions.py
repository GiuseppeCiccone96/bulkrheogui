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

def is_all_same(data): 
    """Checks whether elements of multi dimensional array are of the same length.
    If all elements are of the same length, returns True, else returns False."""
    res = []
    for i in range(len(data)-1):
        if len(data[i+1])==len(data[i]):
            res.append(1)
        else:
            res.append(0)
    if 0 in res:
        return False
    else:
        return True

if __name__ == "__main__":
    pos = [[1,2,3],[4,5,6],[7,8,9]]
    neg = [[1],[1,2,3],[2,4]]
    check = is_all_same(pos)
    check1=is_all_same(neg)
    print(check)
            
            
