import json
import numpy as np
import math

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
    mean_score = np.mean([ii[0] for ii in res_scores])
    std_score = np.std([ii[0] for ii in res_scores])
    mean_speed = np.mean([ii[1] for ii in res_scores])
    std_speed = np.std([ii[1] for ii in res_scores])
    return (1./mean_score, std_score/(math.sqrt(len(res_scores))*mean_score ** 2), 1./mean_speed, std_speed/(math.sqrt(len(res_scores))*mean_speed ** 2))


def main():
    score_val, score_dev, speed_val, speed_dev = score()
    print("Score: %6.5f +/- %1.2f" % (score_val, score_dev))
    print("Speed: %6.5f +/- %1.2f" % (speed_val, speed_dev))

main()
