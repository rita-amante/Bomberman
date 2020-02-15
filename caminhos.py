import math
from tree_search import *

class Caminhos(SearchDomain):
    def __init__(self,connections):
        self.connections = connections
    def actions(self,destino):
        actlist = []
        for (C1,C2,D) in self.connections:        # C1 = [1,1] C2 = [3,3]
            if (C1==destino):
                actlist += [(C1,C2)]
            elif (C2==destino):
               actlist += [(C2,C1)]
        return actlist 
    def result(self,casa,action):
        (C1,C2) = action
        if C1==casa:
            return C2
    def cost(self, cidade, action):
        (C1,C2) = action        # action é tuplo, extrai cidade origem e destino de action
        if C1 != cidade:
            return None
        for (c1,c2,D) in self.connections:
            if action == (c1,c2) or action == (c2,c1):
                return D
        return None
    def heuristic(self, state, goal_state):
        c1_x = state[0]
        c1_y = state[1]
        c2_x = goal_state[0]
        c2_y = goal_state[1]

        return math.hypot(c1_x - c2_x, c1_y - c2_y)