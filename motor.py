import numpy as np 

def getMedCurve(xar, yar, loose=True, threshold=3, error=False):
    """Takes repeated nummerical data (replicates passed as lists, stored in a list) 
    and computes the average and error. Useful for displaying "average" plots
    with error bands.
    
    This function was taken from the following github repo (https://github.com/CellMechLab/nanoindentation),
    author Dr Massimo Vassalli at the Cellular Mechanobiology Lab, University of Glasgow."""

    if loose is False:
        xmin = -np.inf
        xmax = np.inf
        deltax = 0
        nonecount = 0
        for x in xar:
            if x is not None and np.min(x) is not None:
                xmin = np.max([xmin, np.min(x)])
                xmax = np.min([xmax, np.max(x)])
                deltax += ((np.max(x)-np.min(x))/(len(x)-1))
            else:
                nonecount += 1
        deltax /= (len(xar)-nonecount)
        xnew = np.linspace(xmin, xmax, int((xmax-xmin)/(deltax)))
        ynew = np.zeros(len(xnew))
        for i in range(len(xar)):
            if xar[i] is not None and np.min(xar[i]) is not None:
                ycur = np.interp(xnew, xar[i], yar[i])
                ynew += ycur
        ynew /= (len(xar)-nonecount)
    else:
        xmin = np.inf
        xmax = -np.inf
        deltax = 0
        for x in xar:
            try:
                xmin = np.min([xmin, np.min(x)])
                xmax = np.max([xmax, np.max(x)])
                deltax += ((np.max(x) - np.min(x)) / (len(x) - 1))
            except TypeError:
                return
        deltax /= len(xar)
        xnewall = np.linspace(xmin, xmax, int((xmax - xmin) / deltax))
        ynewall = np.zeros(len(xnewall))
        count = np.zeros(len(xnewall))
        ys = np.zeros([len(xnewall), len(xar)])
        for i in range(len(xar)):
            imin = np.argmin((xnewall - np.min(xar[i])) ** 2)  # +1
            imax = np.argmin((xnewall - np.max(xar[i])) ** 2)  # -1
            ycur = np.interp(xnewall[imin:imax], xar[i], yar[i])
            ynewall[imin:imax] += ycur
            count[imin:imax] += 1
            for j in range(imin, imax):
                ys[j][i] = ycur[j-imin]
        cc = count >= threshold
        xnew = xnewall[cc]
        ynew = ynewall[cc] / count[cc]
        yerrs_new = ys[cc]
        yerr = []
        for j in range(len(yerrs_new)):
            squr_sum = 0
            num = 0
            std = 0
            for i in range(0, len(yerrs_new[j])):
                if yerrs_new[j][i] != 0:
                    squr_sum += (yerrs_new[j][i] - ynew[j]) ** 2
                    num += 1
            if num > 0:
                std = np.sqrt(squr_sum / num)
            yerr.append(std)
        yerr = np.asarray(yerr)
    if error == False:
        return xnew[:-1], ynew[:-1]
    elif error == True:
        return xnew[:-1], ynew[:-1], yerr[:-1]


