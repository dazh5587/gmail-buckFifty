totalsum = 0
denom = 52
prevmult = 1
ev = 1
while denom >= 4:
    totalsum+=prevmult*(4.0/denom)*ev
    prevmult*=1.0*(denom-4)/denom
    ev+=1
    denom-=1
print (totalsum)