import json
import numpy as np

def score():
    base_name = "./out/out"
    nr = 10

    res = {}
    for i in range(nr):
        f = open(base_name+str(i), "r")
        res_single = json.loads(f.read())
        res = {**res_single, **res}

    res_scores=[]
    for name in res:
        if (res[name]["optimizer_time"] > 0) and res[name]["coupling_correct_optimized"]:
            # only add the score if the QISKit reference compiler worked well
            if (res[name]["reference_time"] > 0) and res[name]["coupling_correct_reference"]:
                # both user and reference compiler gave the correct result without error
                res_scores.append([res[name]["cost_optimized"]/res[name]["cost_reference"],res[name]["optimizer_time"]/res[name]["reference_time"]])
            else:
                # the user compiler had an error or did not produce the right quantum state
                # this returns a value which is half as good as the reference
                res_scores.append([2,2])
    return (1./np.mean([ii[0] for ii in res_scores]), 1./np.mean([ii[1] for ii in res_scores]))


def main():
    score_val, speed_val = score()
    print("Score: %6.5f" % score_val)
    print("Speed: %6.5f" % speed_val)

main()
