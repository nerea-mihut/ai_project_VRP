import random
#parametrii problemei

nr_clienti = 125
nr_noduri = 126
capacitate_kg= 1500

#parametrii algoritmului

probabilitate_mutatie = 0.05
nr_generatii = 10
dim_populatie = 10 #nr de indivizi per generatie

def generatie_initiala():
    populatie = []
    for i in range (dim_populatie + 1):
        individ = list(range(1, nr_clienti+1))
        random.shuffle(individ) #amestec clientii ca sa fie random in lista
        populatie.append(individ)
    return populatie

populatie = generatie_initiala()
print(populatie)