# This code is adopted from ankit singla RandomRegularGraph.java (Topobench-1)
# I only transform it into python codes

import numpy as np

# n = num of nodes
# swPort = num of port per switch
# netPort = num of network port per switch
# toLink = switch to pair
# degreeUsed = to check if switch has fulfil the network degree

def Jellyfish(n, swPort, netPort):
    print ("Creating Jellyfish Topology with RRG(%s, %s, %s)" % (n, swPort, netPort))
    mat = np.zeros ( (n, n) )

    toLink = []
    degreeUsed = []
    for i in range(n):
        toLink.append(i)
        degreeUsed.append(0)

    stopSign = False
    
    while (len(toLink) != 0 and not stopSign):
        p1 = -1
        p2 = -1
        found = False
        iteration = 1
        
        while (not found and (iteration < 1000)):
            p1 = np.random.randint(len(toLink))
            p2 = p1
            while (p2 == p1):
                p2 = np.random.randint(len(toLink))
            
            src = toLink[p1]
            dst = toLink[p2]
            if (mat[src,dst] != 1 and mat[src,dst] != 1):
                found = True
                mat[src,dst] = 1
                mat[dst,src] = 1
        
        if (iteration > 1000):
            print ('Unable to find new pair for link between: ', toLink)
            stopSign = True
            
        if (not stopSign):
            degreeUsed[p1] += 1
            degreeUsed[p2] += 1
            p1Deleted = False
            if (degreeUsed[p1] == netPort):
                toLink.pop(p1)
                degreeUsed.pop(p1)
                p1Deleted = True
            
            if (p1Deleted and p1 < p2):
                p2 -= 1
            
            if (degreeUsed[p2] == netPort):
                toLink.pop(p2)
                degreeUsed.pop(p2)
        
        if (len(toLink) == 1):
            print ('Remaining just one node to link with degree ', degreeUsed[0], ' out of ', netPort)
            stopSign = True
            
        iteration += 1
    return mat

# =================================================    

n = 5
swPort = 16
netPort = 4

res = Jellyfish(n,swPort,netPort)
print res
for i in range(n):
    for j in range(i+1,n):
        if (res[i,j] == 1):
            print (i, j)
