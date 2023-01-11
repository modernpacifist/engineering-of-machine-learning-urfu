#!/bin/env python3.9

import numpy as np
import statistics


def random_predict(number:int=np.random.randint(1, 101)) -> int:
    count = 0
    lst_num = list(range(1, 101))

    while True:
        count += 1
        predict_number = int(np.mean(lst_num))

        half = round(int(len(lst_num))/2)
        if number == predict_number:
            print(f"secret number was: {predict_number}")
            print(f"number of tries: {count}")
            return predict_number

        if predict_number < number:
            lst_num = lst_num[half:]

        if predict_number > number:
            lst_num = lst_num[:half]

    return None


if __name__ == "__main__":
    for i in range(1000):
        print(random_predict(np.random.randint(1, 101)))
