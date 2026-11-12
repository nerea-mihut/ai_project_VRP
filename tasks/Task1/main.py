# fitness function si reprezentarea individului

# Reprezentarea indivizilor:

indecsi_localitati = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
nr_cars = 3
nr_indivizi = 10

import random

def initial_population():
    population = []
    random.shuffle(indecsi_localitati)
    print(indecsi_localitati)
    for i in range(nr_indivizi):
        individ = [ [] for _ in range(nr_cars) ]
        for j in range(len(indecsi_localitati)):
            individ[j % nr_cars].append(indecsi_localitati[j])
        population.append(individ)
    return population
print(initial_population())

def fitness():
    return 