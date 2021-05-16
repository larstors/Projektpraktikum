#Project Library

#recommended modules (auto-import not possible?)
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt, matplotlib.cm as cm, matplotlib.animation as animation
from IPython.display import HTML
import math

#Section 1: Networks

def undirect_adjacency(matrix):
    #Puts sum of ij and ji cell in both ij and ji cell.
    matrix+=matrix.transpose()

def unweight_adjacency(matrix):
    #Replaces non-zero cell entries with ones.
    for i in range(len(matrix)):
        for j in range(len(matrix)):
            if matrix[i][j]!=0:
                matrix[i][j]=1

#Section 2.1: RKI Data Import
#For definition of intern region numbers -> see ..\Media\region 38 with border (cut).png

def region_setup(mode):
        #takes mode of network: 12 for Region12, 38 for Region38, more to be added
        #returns array of associated RKI LK IDs, label dictionary of the structure: intern_region_number: LK name
        #the following declarations may be moved into a database later
        lk_hildesheim_id=3254
        lk_holzminden_id=3255
        lk_goslar_id=3153
        lk_höxter_id=5762
        lk_northeim_id=3155
        lk_göttingen_id=3159
        lk_harz_id=15085
        lk_kassel_id=6633
        sk_kassel_id=6611
        lk_werrameißnerkreis_id=6636
        lk_eichsfeld_id=16061
        lk_nordhausen_id=16062
        #remaining ids for Region38 to be added
        if(mode==12):
            region_ids=[lk_hildesheim_id,lk_holzminden_id,lk_goslar_id,lk_höxter_id,lk_northeim_id,lk_göttingen_id,lk_harz_id,lk_kassel_id,sk_kassel_id,lk_werrameißnerkreis_id,lk_eichsfeld_id,lk_nordhausen_id]
            region_names=['Hildesheim','Holzminden','Goslar', 'Höxter','Northeim','Göttingen','Harz','Kassel (LK)','Kassel (SK)', 'Werra-Meißner-Kreis','Eichsfeld','Nordhausen']
            labels={}
            for intern_region_number in range(mode):
                labels[intern_region_number]=region_names[intern_region_number]
        elif(mode==38):
            print("mode err: not yet implemented")
        else:
            print("mode err: invalid")
        return region_ids,labels

def import_rki_history(region_ids, n):
    #Takes array of RKI LK IDs and n for required n-day-incidence, returns the following:
    #(0) case matrix with the format [intern_region_number][*][day(since beginning, to be clarified)]
    #   where * can be: (structure may be changed later)
    #   0: new cases at the day before
    #   1: cumulative no. of cases
    #   2: n-day-incidence per 100,000 inhabitants
    #   3: -to be added- new deaths
    #   4: -to be added- cumuative no. of deaths = current D
    #   5: -to be added- new recoverd
    #   6: -to be added- cumulative no. of recovered = current R
    #   7: -to be added- current S
    #   8: -to be added- current I
    #(1) array containing population sizes
    #import case data etc.
    rki=pd.read_csv('External Data/RKI_History.csv', sep=',', header='infer')
    rki=rki.sort_values(by='Datum')
    #write data in arrays
    lk=np.array(rki['AdmUnitId'])
    lk_comp_num=len(lk)
    day=np.array(rki['Datum'])
    case=np.array(rki['AnzFallVortag'])#other options not coherent
    case_cum=np.array(rki['KumFall'])
    #import population data
    pop=pd.read_csv('External Data/RKI_Corona_Landkreise.csv', sep=',', header='infer')
    lk_popcalc=np.array(pop['AdmUnitId'])
    lk_popsize=np.array(pop['EWZ'])
    lk_num=len(lk_popsize)
    #find out number of time steps
    time=len([a for a in lk if a==0])
    dimensions=3 #here: new cases, cumulative cases, 7-day-incidence
    #create and fill regional array
    region_num=len(region_ids)
    region_cases=np.zeros((region_num,dimensions, time))
    region_popsize=np.zeros((region_num))
    for intern_region_number in range(region_num):
        current_time=0
        for i in range(lk_comp_num):
            if lk[i]==region_ids[intern_region_number] and current_time<time:
                region_cases[intern_region_number][0][current_time]=case[i]
                region_cases[intern_region_number][1][current_time]=case_cum[i]
                current_time+=1
        for j in range(lk_num):
            if lk_popcalc[j]==region_ids[intern_region_number]:
                region_popsize[intern_region_number]=lk_popsize[j]
                region_cases[intern_region_number][2]=n_day_incidence(region_cases[intern_region_number][0],region_popsize[intern_region_number],n)
    return region_cases, region_popsize

#Section 2.2: Data Manipulation

def n_day_moving_average(case_array,n):
    output=np.zeros((len(case_array)))
    for i in range(len(case_array)):
        if(i>=n-1):
            isum=0
            for j in range(n):
                isum+=case_array[i-j]
            output[i]=isum
        else:
            output[i]=0 #or undefined, not sure tbh
    return output/n

def n_day_incidence(case_array,pop,n):
    #calculates n-day-incidence per 100,000 inhabitants
    return n*n_day_moving_average(case_array,n)/pop*100000


def effective_population(comFrom, N, i):
    """Function to calculated the effective population in a cell.

    Args:
        comFrom (callable(j)): function that returns commuters from cell.
        N (array): array with population of every cell
        i (integer): the cell of which the effective population is wanted.

    Returns:
        float: the effective population in cell i.
    """
    return N[i] - np.sum(comFrom(i))



def effective_infected(comTo, comFrom, N, i, infected, dimension):
    """Function to calculate the effective number of infected in a cell.

    Args:
        comTo (callable(j)): function that returns array of commuters from cell.
        comFrom (callable(j)): function that returns array of commuters to a cell.
        N (array): array with population of every cell
        i (integer): the cell of which the effective population is wanted.
        infected (array): array with number of infected from every cell
        dimension (integer): number of cells

    Returns:
        float: effective infected in cell i
    """

    # making the value to return
    Ieff = infected[i]
    
    #variables for sum of commuters to and from
    sto = 0
    sfrom = 0
    for k in range(dimension):
        # adding commuters from all cells to i
        sto += comTo(i)[k] * infected[k]
        
        # subtracting commuters from i to all cells
        sfrom -= comFrom(i)[k]
    
    # adjusting for proportionality and applying the normalizing factor
    sfrom *= infected[i]
    
    # adding the change from commuters
    Ieff += (sfrom + sto)/N[i]

    return Ieff






#Section 2.3: Data Visualization














