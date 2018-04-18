from copy import deepcopy
from random import randrange

def main():
    n = 4
    trials = 10000000

    initial = [[x] for x in range(n)]
    wanted = initial[1:]+initial[:1]

    for i in range(trials):
        cop = deepcopy(initial)
        for j in range(3*n-3):
            index1 = randrange(n)
            index2 = randrange(n)
            xor(cop, index1, index2)
            if cop == wanted:
                print(str(j))
                break


def xor(list, i, j):
    list[i]=[x for x in list[i]+list[j] if not (x in list[i] and x in list[j])]


main()
