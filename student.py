# Grupo: Eduardo Coelho (88867), Joaquim Ramos (88812), Rita Amante (89264)


import sys
import json
import asyncio
import websockets
import getpass
import os
import math
import time

from mapa import Map
from caminhos import *
from tree_search import *

steps = []
inicio = [0,0] # valor inutil pois é atualizado logo no primeiro try

# Criar um submap para o mapa todo (usado na funçao de terminar o nivel, ir para a gate)
def criar_submap_todo(mapa):
    return [0,len(mapa.map),0,len(mapa.map[0])]

# Criar um submap entre o bomberman e parede mais proxima
def criar_submap(bomberman,parede):
    if(bomberman[0] < parede[0]):
        xmin = bomberman[0]-2
        xmax = parede[0]+2
    else: 
        xmin = parede[0]-2
        xmax = bomberman[0]+2
    
    if(bomberman[1] < parede[1]):
        ymin = bomberman[1]-2
        ymax = parede[1]+2
    else:
        ymin = parede[1]-2
        ymax = bomberman[1]+2

    return [xmin,xmax,ymin,ymax]

# Criar um submap à volta do bomberman com raio R
def criar_submap_fuga(bomberman,raio):
    xmin = bomberman[0] - raio
    xmax = bomberman[0] + raio
    ymin = bomberman[1] - raio
    ymax = bomberman[1] + raio

    if xmin < 0:
        xmin = 0
    if ymin < 0:
        ymin = 0

    return [xmin,xmax,ymin,ymax]

# Devolve uma lista de ligacoes dentro do submap
#Cria as ligações dentro de um submapa (xmin,xmax,ymin,ymax). Vai começar num canto do retângulo
#que é o submapa e vai perguntar se a coordenada à direita e em baixo é stone ou parede destrutível,
#caso não seja nenhuma das duas pode adicionar a ligação.
def ligacoes(mapa, state_paredes, xmin, xmax, ymin, ymax, bomberman):
    ligacoes=[]
    for l in range (xmin,xmax):             # x = 1 até x = 10
        for c in range (ymin,ymax):
            # Vamos percorrer todas as colunas de cada linha. As linhas são percorridas de cima para baixo.
            # Garantir que nao estamos numa casa que é uma parede
            if not mapa.is_stone((l,c)) and (not [l,c] in state_paredes or [l,c] == bomberman):
                # Adicionamos a ligacao à casa da direita, se ela existir e não for uma parede
                if c < len(mapa.map[l]) and not mapa.is_stone((l,c+1)) and (not [l,c+1] in state_paredes or [l,c+1] == bomberman):
                    ligacoes.append(([l,c],[l,c+1],1))
                # Adicionamos a ligacao à casa de baixo, se ela existir e não for uma parede
                if l < len(mapa.map) and not mapa.is_stone((l+1,c)) and (not [l+1,c] in state_paredes or [l+1,c] == bomberman):
                    ligacoes.append(([l,c],[l+1,c],1))
    #print("\nLIGACOES:")
    #print(ligacoes)
    return ligacoes

# Devolve as coordenadas coladas a parede mais próxima do bomberman 
#Procura a parede mais proxima do bomberman através da hipotenusa. Após calcular qual é a parede
#mais próxima, irá ver qual das 4 coordenadas que rodeiam essa parede, qual delas está mais próxima do
#bomberman.
def proxima_parede(bomberman,state_paredes,mapa):
    minparede = state_paredes[0]
    minhypot = math.hypot(minparede[0] - bomberman[0] ,minparede[1] - bomberman[1])
    # Descobrir parede mais próxima do bomberman
    for parede in state_paredes:
        if math.hypot(parede[0] - bomberman[0], parede[1] - bomberman[1]) < minhypot:
            minparede = parede
            minhypot = math.hypot(parede[0] - bomberman[0], parede[1] - bomberman[1])

    # Descobrir se é mais perto aproximar da parede por cima, baixo, esquerda ou direita
    caminhos_possiveis = []
    cima = [minparede[0], minparede[1] + 1]
    direita = [minparede[0] +1, minparede[1]]
    baixo = [minparede[0], minparede[1] - 1]
    esquerda = [minparede[0] -1, minparede[1]]

    # Das coordenadas em cima, esquerda, direita, baixo, da parede, as que são espaços vazios (possivel o bomberman andar para lá), adicionar ao array caminhos_possiveis
    if not mapa.is_stone(cima) and not cima in state_paredes :
        caminhos_possiveis.append(cima)
    if not mapa.is_stone(direita) and not direita in state_paredes:
        caminhos_possiveis.append(direita)
    if not mapa.is_stone(baixo) and not baixo in state_paredes:
        caminhos_possiveis.append(baixo)
    if not mapa.is_stone(esquerda) and not esquerda in state_paredes:
        caminhos_possiveis.append(esquerda)

    # Caso exista espaços vazios a volta da parede escolhida, ir pra o mais proximo do bomerman
    if caminhos_possiveis != []:
        mincaminho = caminhos_possiveis[0]
        minhypot = math.hypot(mincaminho[0] - bomberman[0], mincaminho[1] - bomberman[1])
        for caminho in caminhos_possiveis:
            if math.hypot(caminho[0] - bomberman[0], caminho[1] - bomberman[1]) < minhypot:
                mincaminho = caminho
                minhypot = math.hypot(caminho[0] - bomberman[0], caminho[1] - bomberman[1])

        result = [mincaminho]
        for caminho in caminhos_possiveis:
            if caminho != mincaminho:
                result.append(caminho)

        return result
    
    # No caso super especifico de a parede mais proxima nao ter nenhum dos 4 espaços ao seu redor limpos, 
    # o bomberman simplesmente anda uma casa para cima, fazendo com que a parede mais proxima asseguir seja outra
    else:
        for x in range (bomberman[0]-3,bomberman[0]+3):
            for y in range (bomberman[1]-3,bomberman[1]+3):
                if not mapa.is_stone((x,y)) and not [x,y] in state_paredes:
                    return [[x,y],0]

# Transforma as coordenadas (p.e. [1,1] [2,1] [2,2]) para letras (p.e. ['d','s'])
#Transforma a lista de coordenadas calculada pelo tsearch numa lista de letras. Isto é feito subtraindo
#uma coordenada pela sua anterior, e através do resultado podemos transformar numa tecla 'w', 'a', 's'
#ou 'd'.
def searchtokeys(tsearch):
    result = []
    if type(tsearch) == tuple:
        search = tsearch[0]
    else:
        search = tsearch
    for i in range(0,len(search)-1):
        origem = search[i]
        destino = search[i+1]
        resultado = [destino[0] - origem[0], destino[1] - origem[1]]
        if resultado== [0,1]:
            result.append('s')
        elif resultado== [0,-1]:
            result.append('w')
        elif resultado == [1,0]:
            result.append('d')
        elif resultado == [-1,0]:
            result.append('a')

    return result

# função que foge de inimigo após perigo, dependendo das coordenadas dele
#Quando fugir de um inimigo, vai ter em conta a posição deste inimigo na escolha do local para onde
#fugir. Por exemplo, caso um inimigo esteja na direção canto superior direito relativamente ao
#bomberman, este tentará primeiro encontrar uma posição segura no canto inferior esquerdo. Caso não
#consiga, tentará encontrar no canto inferior direito e no canto superior esquerdo. Apenas em último
#recurso é que o bomberman acaba por escolher fugir na direção do inimigo devido a não ter mais
#nenhuma hipótese.
def fugir_inimigo(bomberman,mapa,state_paredes,raio,inimigo):  
    result = [bomberman[0] - inimigo[0], bomberman[1] - inimigo[1]]
    if result[0]<=0 and result[1]>=0: # se inimigo topright, bomberman [5,5] inimigo [7,2], result = [-2,3] 
        #"topright"
        xmin = bomberman[0] - raio
        xmax = bomberman[0]
        ymin = bomberman[1]
        ymax = bomberman[1] + raio

        xmin2 = bomberman[0]
        xmax2 = bomberman[0] + raio
        ymin2 = bomberman[1]
        ymax2 = bomberman[1] + raio

        xmin3 = bomberman[0] - raio
        xmax3 = bomberman[0]
        ymin3 = bomberman[1] - raio
        ymax3 = bomberman[1]

    elif result[0]>=0 and result[1]>=0: # se inimigo topleft, bomberman[5,5] inimigo [3,3], result = [2,2]
        #"topleft"
        xmin = bomberman[0]
        xmax = bomberman[0] + raio
        ymin = bomberman[1]
        ymax = bomberman[1] + raio

        xmin2 = bomberman[0]
        xmax2 = bomberman[0] + raio
        ymin2 = bomberman[1] - raio
        ymax2 = bomberman[1]

        xmin3 = bomberman[0] - raio
        xmax3 = bomberman[0]
        ymin3 = bomberman[1]
        ymax3 = bomberman[1] + raio


    elif result[0]>=0 and result[1]<=0: # se inimigo bot left, bomberman[5,5] inimigo [3,7], result = [2,-2]
        #"botleft"
        xmin = bomberman[0]
        xmax = bomberman[0] + raio
        ymin = bomberman[1] - raio
        ymax = bomberman[1]

        xmin2 = bomberman[0] - raio
        xmax2 = bomberman[0]
        ymin2 = bomberman[1] - raio
        ymax2 = bomberman[1]

        xmin3 = bomberman[0]
        xmax3 = bomberman[0] + raio
        ymin3 = bomberman[1]
        ymax3 = bomberman[1] + raio


    else:
        #"botright"
        xmin = bomberman[0] - raio
        xmax = bomberman[0]
        ymin = bomberman[1] - raio
        ymax = bomberman[1]

        xmin2 = bomberman[0] - raio
        xmax2 = bomberman[0]
        ymin2 = bomberman[1]
        ymax2 = bomberman[1] + raio

        xmin3 = bomberman[0]
        xmax3 = bomberman[0] + raio
        ymin3 = bomberman[1] - raio
        ymax3 = bomberman[1]

    search = None
    submap = criar_submap_fuga(bomberman,raio+2)
    connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bomberman)
    caminhos_possiveis = Caminhos(connections) 

    for x in range (xmin,xmax):
        for y in range (ymin,ymax):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+1)
                if search != None and len(search) > 1:
                    return searchtokeys(search)

    for x in range (xmin,xmax):
        for y in range (ymin,ymax):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+2)
                if search != None and len(search) > 1:
                    return searchtokeys(search)

    for x in range (xmin,xmax):
        for y in range (ymin,ymax):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+3)
                if search != None and len(search) > 1:
                    return searchtokeys(search)

    for x in range (xmin2,xmax2):
        for y in range (ymin2,ymax2):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+1)
                if search != None and len(search) > 1:
                    return searchtokeys(search)

    for x in range (xmin2,xmax2):
        for y in range (ymin2,ymax2):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+2)
                if search != None and len(search) > 1:
                    return searchtokeys(search)
                
    for x in range (xmin2,xmax2):
        for y in range (ymin2,ymax2):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+3)
                if search != None and len(search) > 1:
                    return searchtokeys(search)
    
    for x in range (xmin3,xmax3):
        for y in range (ymin3,ymax3):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+1)
                if search != None and len(search) > 1:
                    return searchtokeys(search)

    for x in range (xmin3,xmax3):
        for y in range (ymin3,ymax3):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+2)
                if search != None and len(search) > 1:
                    return searchtokeys(search)

    for x in range (xmin3,xmax3):
        for y in range (ymin3,ymax3):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+3)
                if search != None and len(search) > 1:
                    return searchtokeys(search)
    
    # Se não conseguiu nenhum caminho para longe do inimigo, opta pela função normal de fugir (onde pode fugir para ele, mas é a unica opçao)
    return fugir(bomberman,mapa,state_paredes,raio)
    
    

def fugir(bomberman,mapa,state_paredes,raio):
    #print(state_paredes)
    if raio > 9:
        submap = criar_submap(bomberman,inicio)
        connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bomberman)
        caminhos_possiveis = Caminhos(connections) 
        p = SearchProblem(caminhos_possiveis,bomberman,inicio)
        t = SearchTree(p,'greedy')
        result = t.search()
        if result != None:
            print("FUGIU PARA O INICIO!")
            return searchtokeys(t.search())
        else:
            return []

    search = None
    submap = criar_submap_fuga(bomberman,raio+1)
    connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bomberman)
    caminhos_possiveis = Caminhos(connections) 

    for x in range (bomberman[0]-raio,bomberman[0]+raio):
        for y in range (bomberman[1]-raio,bomberman[1]+raio):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+1)
                if search != None and len(search) > 1:
                    return searchtokeys(search)

    for x in range (bomberman[0]-raio,bomberman[0]+raio):
        for y in range (bomberman[1]-raio,bomberman[1]+raio):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+2)
                if search != None and len(search) > 1:
                    return searchtokeys(search)
    #print("SEARCHH:")
    #print(search)
    return fugir(bomberman,mapa,state_paredes,raio+1)


# função que foge de inimigo após perigo, dependendo das coordenadas dele
def fugir_inimigo_bomba(bomberman,mapa,state_paredes,raio,inimigo,coorBombRange):  
    result = [bomberman[0] - inimigo[0], bomberman[1] - inimigo[1]]
    if result[0]<=0 and result[1]>=0: # se inimigo topright, bomberman [5,5] inimigo [7,2], result = [-2,3] 
        #"topright"
        xmin = bomberman[0] - raio
        xmax = bomberman[0]
        ymin = bomberman[1]
        ymax = bomberman[1] + raio

        xmin2 = bomberman[0]
        xmax2 = bomberman[0] + raio
        ymin2 = bomberman[1]
        ymax2 = bomberman[1] + raio

        xmin3 = bomberman[0] - raio
        xmax3 = bomberman[0]
        ymin3 = bomberman[1] - raio
        ymax3 = bomberman[1]

    elif result[0]>=0 and result[1]>=0: # se inimigo topleft, bomberman[5,5] inimigo [3,3], result = [2,2]
        #"topleft"
        xmin = bomberman[0]
        xmax = bomberman[0] + raio
        ymin = bomberman[1]
        ymax = bomberman[1] + raio

        xmin2 = bomberman[0]
        xmax2 = bomberman[0] + raio
        ymin2 = bomberman[1] - raio
        ymax2 = bomberman[1]

        xmin3 = bomberman[0] - raio
        xmax3 = bomberman[0]
        ymin3 = bomberman[1]
        ymax3 = bomberman[1] + raio


    elif result[0]>=0 and result[1]<=0: # se inimigo bot left, bomberman[5,5] inimigo [3,7], result = [2,-2]
        #"botleft"
        xmin = bomberman[0]
        xmax = bomberman[0] + raio
        ymin = bomberman[1] - raio
        ymax = bomberman[1]

        xmin2 = bomberman[0] - raio
        xmax2 = bomberman[0]
        ymin2 = bomberman[1] - raio
        ymax2 = bomberman[1]

        xmin3 = bomberman[0]
        xmax3 = bomberman[0] + raio
        ymin3 = bomberman[1]
        ymax3 = bomberman[1] + raio


    else:
        #"botright"
        xmin = bomberman[0] - raio
        xmax = bomberman[0]
        ymin = bomberman[1] - raio
        ymax = bomberman[1]

        xmin2 = bomberman[0] - raio
        xmax2 = bomberman[0]
        ymin2 = bomberman[1]
        ymax2 = bomberman[1] + raio

        xmin3 = bomberman[0]
        xmax3 = bomberman[0] + raio
        ymin3 = bomberman[1] - raio
        ymax3 = bomberman[1]

    search = None
    submap = criar_submap_fuga(bomberman,raio+2)
    connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bomberman)
    caminhos_possiveis = Caminhos(connections) 

    for x in range (xmin,xmax):
        for y in range (ymin,ymax):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+1)
                #if search != None:
                #    print(search)
                #    print(search[0][-1])
                #    print(search[0][-1][0])
                #    print(inimigo)
                #    print(inimigo[0])
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)

    for x in range (xmin,xmax):
        for y in range (ymin,ymax):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+2)
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)

    for x in range (xmin,xmax):
        for y in range (ymin,ymax):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+3)
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)

    for x in range (xmin2,xmax2):
        for y in range (ymin2,ymax2):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+1)
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)

    for x in range (xmin2,xmax2):
        for y in range (ymin2,ymax2):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+2)
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)
                
    for x in range (xmin2,xmax2):
        for y in range (ymin2,ymax2):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+3)
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)
    
    for x in range (xmin3,xmax3):
        for y in range (ymin3,ymax3):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+1)
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)

    for x in range (xmin3,xmax3):
        for y in range (ymin3,ymax3):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+2)
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)

    for x in range (xmin3,xmax3):
        for y in range (ymin3,ymax3):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+3)
                if search != None and not search[0][-1] in coorBombRange and search[0][-1][0] != inimigo[0] and search[0][-1][1] != inimigo[1]:
                    return searchtokeys(search)
    
    # Se não conseguiu nenhum caminho para longe do inimigo, opta pela função normal de fugir (onde pode fugir para ele, mas é a unica opçao)
    return fugir_bomba(bomberman,mapa,state_paredes,raio,coorBombRange)

def fugir_bomba(bomberman,mapa,state_paredes,raio,coorBombRange):
    #print(state_paredes)
    if raio > 9:
        submap = criar_submap(bomberman,inicio)
        connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bomberman)
        caminhos_possiveis = Caminhos(connections) 
        p = SearchProblem(caminhos_possiveis,bomberman,inicio)
        t = SearchTree(p,'greedy')
        result = t.search()
        if result != None:
            return searchtokeys(t.search())
        else:
            return None

    search = None
    submap = criar_submap_fuga(bomberman,raio+1)
    connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bomberman)
    caminhos_possiveis = Caminhos(connections) 

    for x in range (bomberman[0]-raio,bomberman[0]+raio):
        for y in range (bomberman[1]-raio,bomberman[1]+raio):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+1)
                if search != None and not search[-1] in coorBombRange:
                    return searchtokeys(search)

    for x in range (bomberman[0]-raio,bomberman[0]+raio):
        for y in range (bomberman[1]-raio,bomberman[1]+raio):
            if not mapa.is_stone((x,y)) and not [x,y] in state_paredes and x!=bomberman[0] and y!=bomberman[1]:
                p = SearchProblem(caminhos_possiveis,bomberman,[x,y])
                t = SearchTree(p,'greedy')
                search = t.searchlimit(raio+2)
                if search != None and not search[-1] in coorBombRange:
                    return searchtokeys(search)
    #print("SEARCHH:")
    #print(search)
    return fugir_bomba(bomberman,mapa,state_paredes,raio+1,coorBombRange)

# Calcula o inimigo mais próximo
def closest_enemy(bomberman,state_enemies):
    m=5000
    enemy=[]
    enemyname = ''
    if state_enemies != []:
        for inimigo in state_enemies:
            posinimigo = inimigo['pos']
            if math.hypot(posinimigo[0] - bomberman[0], posinimigo[1] - bomberman[1]) < m:
                m=math.hypot(posinimigo[0] - bomberman[0], posinimigo[1] - bomberman[1])
                enemy=[posinimigo[0],posinimigo[1]]
                enemyname=inimigo['name']
    return [enemy,m,enemyname]

#Calcula qual o inimigo mais proximo através da hipotenusa e devolve o tsearch com o caminho para
#chegar a ele (se existir). Caso esteja no nivel 4 e ainda não tenha o powerup desse nivel, não tenta seguir
#Minvo's para evitar ciclos infinitos.
def chase_fugitivos(bomberman,state_enemies,mapa,state_paredes,state_level,powerupcount):
    fugitivo_list = []
    if (state_level == 4 and powerupcount < 4):
        for inimigo in state_enemies:
            if inimigo['name'] != 'Minvo':
                fugitivo_list.append(inimigo)
    else:
        for inimigo in state_enemies:
            #if inimigo['name'] != 'Balloom':
            fugitivo_list.append(inimigo)

    if fugitivo_list != []:
        minfugitivo = fugitivo_list[0]
        minhypot = math.hypot(minfugitivo['pos'][0] - bomberman[0], minfugitivo['pos'][1] - bomberman[1])
        for enemie in fugitivo_list:
            if math.hypot(enemie['pos'][0] - bomberman[0], enemie['pos'][0] - bomberman[1]) < minhypot:
                minfugitivo = enemie
                minhypot = math.hypot(enemie['pos'][0] - bomberman[0], enemie['pos'][0] - bomberman[1])

        submap = criar_submap(bomberman, minfugitivo['pos'])
        connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bomberman)
        caminhos_possiveis = Caminhos(connections)
        p = SearchProblem(caminhos_possiveis,bomberman,minfugitivo['pos'])
        t = SearchTree(p,'greedy')
        
        return [t.search() , minfugitivo['name']]
    else:
        return [None, 'Minvo']


async def agent_loop(server_address="localhost:8000", agent_name="student"):
    async with websockets.connect(f"ws://{server_address}/player") as websocket:

        # Receive information about static game properties
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))
        msg = await websocket.recv()

        game_properties = json.loads(msg)

        # You can create your own map representation or use the game representation:
        mapa = Map(size=game_properties["size"], mapa=game_properties["map"])  
        bomba = False
        
        #distancia do target enemy
        detonator = False   #Variável booleana que é alterada para True após apanhar o powerup Detonator. É necessária para saber se envio teclas de espera ou se envio a tecla 'A' para rebentar a bomba.
        pesquisa_none = 0   #Variável usada para o caso em que não exista caminho para o inimigo mais próximo (pode ser devido ao submapa ser pequeno) o bomberman irá destruir paredes 
        ninguem_morreu = 0  #Variável usada para quebrar loops infinitos onde o bomberman vai para o inimigo mas não o mata. Após tentar matar 5 vezes, caso não tenha matado o inimigo, desiste e vai destruir paredes.
        rangeperigo = 3     #Variável que decide a distância que faz o bomberman entrar no 'if de perigo'. Esta variável sofre mudanças num conjunto de if's iniciais, pois o seu melhor valor depende de qual inimigo estamos a fugir.
        powerupcount = 0    #Variável para contar os powerups apanhado. Só vai para a exit caso o powerupcount seja igual ao nivel onde estou.
        currEnemie = 'Balloom'
        fimnivel = 0
        nao_fiques_a_dar_voltas_ao_mapa_atras_dele_por_favor = 0    #Variável usada para quando já não há paredes, como não podemos quebrar os loops ao ir destruir paredes, temos de diminuir o range para os conseguir matar (aproximar mais dos inimigos).
        vidas = 3           #Variável usada para quando o bomberman morre, limpar o queue de teclas.
        wallpass = False    #É necessária para saber se considero as paredes destrutiveis na pesquisa de inimigos ou não.
        variavel = 0
        debug = 0
        inicio = [0,0]

        while True:
            try:
                state = json.loads(
                    await websocket.recv()
                )  # receive game state, this must be called timely or your game will get out of sync with the server
                
                while len(websocket.messages)!=0:
                    state = json.loads(
                        await websocket.recv()
                    ) 
                
                if len(state) == 1:          #jogo acaba por morrer 3 vezes - return -1
                    return -1

                if (state['level'] == 15 and state['enemies'] == []):
                    return 0

                bombermanXY = state['bomberman']    # posição atual do bomberman neste step
                state_paredes = state['walls']
                state_enemies = state['enemies']

                if state['lives'] < vidas:
                    steps.clear()
                    vidas -= 1
                near_enemy=closest_enemy(bombermanXY, state_enemies)


                # guarda coordenada do canto superior esquerdo do mapa
                if (state['level'] == 1 and state['step'] == 1):
                    for y in range (0,len(mapa.map[0])):             # x = 1 até x = 10
                        for x in range (0,len(mapa.map)):
                            if not mapa.is_stone((x,y)):
                                inicio = [x,y]
                                break
                        if inicio != [0,0]:
                            break


                if state['step'] == 1:
                    powerupcount = state['level'] - 1

                # não perde tempo a apanhar powerups que nós não vamos usar
                if (state['level'] == 4 and state['step'] == 1):
                    powerupcount = 3

                if (state['level'] == 2 or state['level'] == 5 or state['level'] == 6 or state['level'] == 8 or state['level'] == 11 or state['level'] == 12 or state['level'] == 13 or state['level'] == 14):
                    powerupcount = state['level']
                


                if state_paredes == [] and state_enemies != [] and near_enemy[2] != 'Balloom':
                    if nao_fiques_a_dar_voltas_ao_mapa_atras_dele_por_favor == 0:
                        rangeperigo = 2.7
                        nao_fiques_a_dar_voltas_ao_mapa_atras_dele_por_favor += 1
                    else:
                        rangeperigo = 2
                        nao_fiques_a_dar_voltas_ao_mapa_atras_dele_por_favor += 1
                        if nao_fiques_a_dar_voltas_ao_mapa_atras_dele_por_favor == 3:
                            nao_fiques_a_dar_voltas_ao_mapa_atras_dele_por_favor = 0
                elif state_enemies != [] and (near_enemy[2] == 'Balloom' or near_enemy[2] == 'Doll'):
                    rangeperigo = 3
                elif state_enemies != [] and (currEnemie == 'Oneal' or currEnemie == 'Kondoria'):# and detonator == False:
                    if detonator:
                        rangeperigo = 2.1
                    else:
                        rangeperigo = 1.9
                elif state_paredes != [] and len(state_enemies) == 1 and near_enemy[2] != 'Balloom' and near_enemy[2] != 'Doll':
                    rangeperigo = 2
                else:
                    if near_enemy[2] == 'Minvo':
                        rangeperigo = 2.7
                    else:
                        rangeperigo = 2.9


                # PRIMEIRO IF: PERIGO! Se existe algum algum inimigo a uma distancia de 'rangeperigo', meter bomba e fugir: 
                if state_enemies != [] and near_enemy[1]<=rangeperigo and ninguem_morreu < 5 and variavel == 0:
                    steps.clear()
                    state_enemies_pos = []
                    for inimigo in state_enemies:
                        state_enemies_pos.append(inimigo['pos'])
                    state_paredes.extend(state_enemies_pos)

                    if state['bombs'] == []:        #caso seja uma fuga de inimigo sem bomba, mete bomba
                        steps.append('B')
                        if wallpass:
                            inimigosComoParedes = []
                            inimigosComoParedes.append([near_enemy[0][0], near_enemy[0][1]])
                            inimigosComoParedes.append([near_enemy[0][0]+1,near_enemy[0][1]])
                            inimigosComoParedes.append([near_enemy[0][0]-1,near_enemy[0][1]])
                            inimigosComoParedes.append([near_enemy[0][0],near_enemy[0][1]+1])
                            inimigosComoParedes.append([near_enemy[0][0],near_enemy[0][1]-1])
                            if bombermanXY in inimigosComoParedes:
                                inimigosComoParedes.remove(bombermanXY)

                            steps.extend(fugir_inimigo(bombermanXY,mapa,state_enemies,2,near_enemy[0]))
                        else:
                            state_paredes.append([near_enemy[0][0], near_enemy[0][1]])
                            state_paredes.append([near_enemy[0][0]+1,near_enemy[0][1]])
                            state_paredes.append([near_enemy[0][0]-1,near_enemy[0][1]])
                            state_paredes.append([near_enemy[0][0],near_enemy[0][1]+1])
                            state_paredes.append([near_enemy[0][0],near_enemy[0][1]-1])
                            if bombermanXY in state_paredes:
                                state_paredes.remove(bombermanXY)

                            steps.extend(fugir_inimigo(bombermanXY,mapa,state_paredes,2,near_enemy[0]))

                    else:                           #caso seja uma fuga de inimigo com bomba ativa, vai adicionar as coordenada de explosao da bomba como paredes
                        coorBombRange = []
                        bombastate = state['bombs'][0]
                        for x in range(bombastate[0][0] - bombastate[2], bombastate[0][0] + bombastate[2]): # coordanada x da bomba - range até x da bomba + range
                            coorBombRange.append([x,bombastate[0][1]])
                        for y in range(bombastate[0][1] - bombastate[2], bombastate[0][1] + bombastate[2]): # coordanada y da bomba - range até y da bomba + range
                            coorBombRange.append([bombastate[0][0],y])

                        state_paredes.append([bombastate[0][0] - bombastate[2], bombastate[0][1]])
                        state_paredes.append([bombastate[0][0], bombastate[0][1] + bombastate[2]])
                        state_paredes.append([bombastate[0][0] + bombastate[2], bombastate[0][1]])
                        state_paredes.append([bombastate[0][0], bombastate[0][1] - bombastate[2]])

                        state_paredes.append([near_enemy[0][0]+1,near_enemy[0][1]])
                        state_paredes.append([near_enemy[0][0]-1,near_enemy[0][1]])
                        state_paredes.append([near_enemy[0][0],near_enemy[0][1]+1])
                        state_paredes.append([near_enemy[0][0],near_enemy[0][1]-1])

                        if wallpass:
                            inimigosComoParedes = []
                            inimigosComoParedes.append([near_enemy[0][0], near_enemy[0][1]])
                            inimigosComoParedes.append([near_enemy[0][0]+1,near_enemy[0][1]])
                            inimigosComoParedes.append([near_enemy[0][0]-1,near_enemy[0][1]])
                            inimigosComoParedes.append([near_enemy[0][0],near_enemy[0][1]+1])
                            inimigosComoParedes.append([near_enemy[0][0],near_enemy[0][1]-1])
                            state_paredes = inimigosComoParedes

                        if bombermanXY in state_paredes:
                            state_paredes.remove(bombermanXY)

                        conta = fugir_inimigo_bomba(bombermanXY,mapa,state_paredes,2,near_enemy[0],coorBombRange)
                        if conta != None:
                            steps.extend(conta)
                        else:
                            steps.extend(fugir_inimigo(bombermanXY,mapa,state['walls'],2,near_enemy[0]))

                    if detonator:
                        steps.extend(['A',''])
                    else:
                        steps.extend(['','','','','','','',''])
                    await websocket.send(
                        json.dumps({"cmd": "key", "key": steps.pop(0)}) # retira e envia a primeira tecla no queue, First In First Out
                    )
                    bomba = False
                    ninguem_morreu += 1
                    variavel += 1
                    
                    
                # SEGUNDO IF: Se existe teclas no queue, enviar uma a uma por try
                elif steps != []: # 'comer' as teclas que estão em queue
                    await websocket.send(
                        json.dumps({"cmd": "key", "key": steps.pop(0)}) # retira e envia a primeira tecla no queue, First In First Out
                    )

                # ELSE:
                else:
                    variavel = 0
                    # Se existir powerups no chão, ir apanhar
                    if state['powerups'] != [] and ninguem_morreu < 6:
                        if state['powerups'][0][1] == 'Detonator':
                            detonator = True
                        if state['powerups'][0][1] == 'Wallpass':
                            wallpass = True
                        powerups = state['powerups']
                        powerup = powerups[0][0]
                        submap = criar_submap(bombermanXY, powerup)
                        if state['exit'] != []:
                            state_paredes.append(state['exit'])

                        connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bombermanXY)
                        caminhos_possiveis = Caminhos(connections)
                        p = SearchProblem(caminhos_possiveis,bombermanXY,powerup)
                        t = SearchTree(p,'greedy')
                        result = t.search()
                        if result != None:
                            steps.extend(searchtokeys(result))
                            if not (state['level'] == 2 or state['level'] == 5 or state['level'] == 6 or state['level'] == 8 or state['level'] == 11 or state['level'] == 12 or state['level'] == 13 or state['level'] == 14):
                                powerupcount += 1
                        else:
                            ninguem_morreu += 1
                    
                    # ELSE:
                    else:
                        # ninguem_morreu é para ciclos viciosos de "aproximar de inimigo" "meter bomba" "fugir" que não matam ninguem,
                        #  após 4 tentativas desiste e vai destruir paredes durante 6 ciclos (10-4)
                        if ninguem_morreu > 4:
                            ninguem_morreu +=1
                            if wallpass:
                                if ninguem_morreu > 6:
                                    ninguem_morreu = 0
                            else:
                                if ninguem_morreu > 10:
                                    ninguem_morreu = 0

                        # Tenta encontrar um caminho para o inimigo mais próximo
                        pesquisa = [None]
                        if state['enemies'] != [] and (state['enemies'][-1]['name'] != 'Balloom') and pesquisa_none < 1 and ninguem_morreu <6 and state['level'] > 1:
                            if wallpass:
                                pesquisa = chase_fugitivos(bombermanXY,state_enemies,mapa,[],state['level'],powerupcount)
                            else:
                                pesquisa = chase_fugitivos(bombermanXY,state_enemies,mapa,state_paredes,state['level'],powerupcount)

                        # Caso encontre caminho para o inimigo mais próximo, vai até o inimigo (a função perigo irá detetar o inimigo proximo e por bomba)
                        if pesquisa[0] != None:
                            steps.clear()
                            steps.extend([''])
                            steps.extend(searchtokeys(pesquisa[0]))
                            currEnemie = pesquisa[1]
                            if steps != []:
                                await websocket.send(
                                    json.dumps({"cmd": "key", "key": steps.pop(0)}) # retira e envia a primeira tecla no queue, First In First Out
                                )
                        
                        # Se não existir caminho para o mais proximo:
                        else:
                            
                            # Caso não encontramos nenhum caminho para algum inimigo, vamos partir paredes durante 14 ciclos
                            pesquisa_none += 1
                            if pesquisa_none == 16:
                                pesquisa_none = 0

                            # PRIORIDADE MÁXIMA: ACABAR O NIVEL: Caso não haja inimigos, já temos as coordenadas da saida, e já apanhamos o powerup deste nivel
                            if state_enemies == [] and state['exit'] != [] and powerupcount >= state['level'] and fimnivel == 0:
                                gate = state['exit']
                                submap = criar_submap(bombermanXY,gate)
                                connections = ligacoes(mapa,state['walls'],submap[0],submap[1],submap[2],submap[3],bombermanXY)
                                caminhos_possiveis = Caminhos(connections)
                                p = SearchProblem(caminhos_possiveis,bombermanXY,gate)
                                t = SearchTree(p,'greedy')
                                result = t.search()
                                if result == None:
                                    fimnivel += 1
                                    bomba = False
                                else:
                                    steps.extend(['',''])
                                    steps.extend(searchtokeys(result))

                            # Caso não haja paredes, mas haja inimigos:
                            elif state_paredes == [] and state_enemies != []:
                                # Caso os inimigos restantes sejam balões, usar a tática de por bombas no canto
                                if state_enemies[-1]['name'] == 'Balloom':
                                    submap = criar_submap(bombermanXY, inicio)
                                    state_enemies_pos = []

                                    for inimigo in state_enemies:
                                        state_enemies_pos.append(inimigo['pos'])
                                    state_paredes.extend(state_enemies_pos)
                                            
                                    connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bombermanXY)
                                    caminhos_possiveis = Caminhos(connections)
                                    p = SearchProblem(caminhos_possiveis,bombermanXY,inicio)
                                    t = SearchTree(p,'greedy')
                                    result = t.search()
                                    if result != None:
                                        steps.extend(searchtokeys(result))

                                    else:
                                        steps.append('')
                                
                                # Senão, temos de caçar os inimigos que fogem de nós
                                else:
                                    # Tenta encontrar um caminho para o inimigo mais próximo
                                    pesquisa = [None]
                                    if state['enemies'] != [] and (state['enemies'][-1]['name'] != 'Balloom') and pesquisa_none < 1 and ninguem_morreu <5 and state['level'] > 1:
                                        pesquisa = chase_fugitivos(bombermanXY,state_enemies,mapa,state_paredes,state['level'],powerupcount)

                                    # Caso encontre caminho para o inimigo mais próximo, vai até o inimigo (a função perigo irá detetar o inimigo proximo e por bomba)
                                    if pesquisa[0] != None:
                                        steps.clear()
                                        steps.extend([''])
                                        steps.extend(searchtokeys(pesquisa[0]))
                                        currEnemie = pesquisa[1]
                                        if steps != []:
                                            await websocket.send(
                                                json.dumps({"cmd": "key", "key": steps.pop(0)}) # retira e envia a primeira tecla no queue, First In First Out
                                            )

                            # Caso haja paredes (só chega aqui se nao encontrou caminho para um inimigo - esta é a funçao de ir partir paredes)
                            elif not bomba: # variavél bomba decide se estamos na fase de andar até a parede, ou na fase de colocar bomba na parede e fugir
                                if fimnivel > 0:
                                    fimnivel += 1
                                if fimnivel > 2:
                                    fimnivel = 0

                                if state['walls'] != []:
                                    parede = proxima_parede(bombermanXY,state['walls'],mapa)
                                else:
                                    parede = [state['exit'],0]
                                submap = criar_submap(bombermanXY, parede[0])

                                if state_enemies != []:
                                    state_enemies_pos = []

                                    for inimigo in state_enemies:
                                        state_enemies_pos.append(inimigo['pos'])

                                    state_paredes.extend(state_enemies_pos)
                                    state_paredes.append([near_enemy[0][0]+1,near_enemy[0][1]])
                                    state_paredes.append([near_enemy[0][0]-1,near_enemy[0][1]])
                                    state_paredes.append([near_enemy[0][0],near_enemy[0][1]+1])
                                    state_paredes.append([near_enemy[0][0],near_enemy[0][1]-1])

                                    if bombermanXY in state_paredes:
                                        state_paredes.remove(bombermanXY)

                                connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bombermanXY)
                                caminhos_possiveis = Caminhos(connections)
                                p = SearchProblem(caminhos_possiveis,bombermanXY,parede[0])
                                t = SearchTree(p,'greedy')
                                search = t.search()
                                if search != None:
                                    steps.extend(searchtokeys(search))
                                elif len(parede) > 1:
                                    submap = criar_submap(bombermanXY, parede[1])
                                    connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bombermanXY)
                                    caminhos_possiveis = Caminhos(connections)
                                    p = SearchProblem(caminhos_possiveis,bombermanXY,parede[1])
                                    t = SearchTree(p,'greedy')
                                    search = t.search()
                                    if search != None:
                                        steps.extend(searchtokeys(search))
                                else: 
                                    submap = criar_submap(bombermanXY, inicio)
                                    connections = ligacoes(mapa,state_paredes,submap[0],submap[1],submap[2],submap[3],bombermanXY)
                                    caminhos_possiveis = Caminhos(connections)
                                    p = SearchProblem(caminhos_possiveis,bombermanXY,inicio)
                                    t = SearchTree(p,'greedy')
                                    search = t.search()
                                    if search != None:
                                        steps.extend(searchtokeys(search))
                                    else:
                                        if debug == 0:
                                            steps.extend(['w','w','w','w','w','w','w','w','w','w','w','w','w','w','w'])
                                            debug += 1
                                        elif debug == 1:
                                            steps.extend(['s','s','s','s','s','s','s','s','s','s','s','s','s','s','s'])
                                            debug += 1
                                        elif debug == 2:
                                            steps.extend(['a','a','a','a','a','a','a','a','a','a','a','a','a','a','a'])
                                            debug += 1
                                        else:
                                            steps.extend(['d','d','d','d','d','d','d','d','d','d','d','d','d','d','d'])
                                            debug = 0


                                bomba = not bomba
                                if steps != []:
                                    await websocket.send(
                                        json.dumps({"cmd": "key", "key": steps.pop(0)}) # retira e envia a primeira tecla no queue, First In First Out
                                    )
                            # fase de colocar bomba e fugir
                            else: 
                                if fimnivel > 0:
                                    fimnivel += 1
                                if fimnivel > 2:
                                    fimnivel = 0
                                steps.append('B')
                                if state_enemies != []:
                                    if wallpass:
                                        steps.extend(fugir_inimigo(bombermanXY,mapa,state_enemies,2,near_enemy[0]))
                                    else:
                                        state_enemies_pos = []

                                        for inimigo in state_enemies:
                                            state_enemies_pos.append(inimigo['pos'])

                                        state_paredes.extend(state_enemies_pos)
                                        steps.extend(fugir_inimigo(bombermanXY,mapa,state_paredes,2,near_enemy[0]))
                                else:
                                    steps.extend(fugir(bombermanXY,mapa,state_paredes,2))
                                if detonator:
                                    steps.extend(['A',''])
                                else:
                                    steps.extend(['','','','','','','',''])
                                bomba = not bomba
                                await websocket.send(
                                    json.dumps({"cmd": "key", "key": steps.pop(0)}) # retira e envia a primeira tecla no queue, First In First Out
                                )
                                
            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return

# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='bombastico' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))