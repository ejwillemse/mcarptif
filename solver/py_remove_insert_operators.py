'''
Created on 29 Jan 2012

@author: elias
'''
class remove_insert_CARP():
    
    def __init__(self, info):
        self.info = info
        self.depot = info.depotnewkey
        self.d = info.d

    def check_depot_position_remove(self, route, position):
        if position == 0: pre_arc = self.depot
        else: pre_arc = route[position - 1]
        if position == len(route) - 1: post_arc = self.depot
        else: post_arc = route[position + 1]        
        return(pre_arc, post_arc)

    def check_depot_position_insert(self, route, position):
        if position-1 > len(route):
            print(route, position)
        if position == 0: pre_arc = self.depot
        else: pre_arc = route[position-1]
        if position == len(route): post_arc = self.depot
        else: post_arc = route[position]        
        return(pre_arc, post_arc)

    def split_route_cost(self, route, position):
        (pre_arc, post_arc) = self.check_depot_position_insert(route, position)
        split_cost = self.d[pre_arc][post_arc]
        return(split_cost, pre_arc, post_arc)
        
    def remove_from_route(self, route, position):
        arc = route[position]
        (pre_arc, post_arc) = self.check_depot_position_remove(route, position)
        remove_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]
        shift_cost = self.d[pre_arc][post_arc]
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)
    
    def insert_in_route(self, route, position, arc):
        (pre_arc, post_arc) = self.check_depot_position_insert(route, position)
        split_cost = self.d[pre_arc][post_arc]
        insert_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]
        net_insert_cost = insert_cost - split_cost
        return(net_insert_cost, split_cost, insert_cost)
    
    def replace_in_route(self, route, position, arc):
        replace_arc = route[position]
        (pre_arc, post_arc) = self.check_depot_position_remove(route, position)
        remove_cost = self.d[pre_arc][replace_arc] + self.d[replace_arc][post_arc]
        insert_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]
        net_replace_cost = insert_cost - remove_cost
        return(net_replace_cost, remove_cost, insert_cost)

    def link_routes(self, route_i, i_pos, route_j, j_pos, arc_i, arc_j):
        adjust_extra = 0
        if i_pos == 0: 
            pre_arc_i = self.depot
            if j_pos == len(route_j): adjust_extra = self.info.dumpCost
        else: pre_arc_i = route_i[i_pos - 1]
        if j_pos == 0: pre_arc_j = self.depot
        else: pre_arc_j = route_j[j_pos - 1]
        if j_pos == len(route_j): arc_j = self.depot
        net_cost_i = self.d[pre_arc_i][arc_j] - self.d[pre_arc_i][arc_i] - adjust_extra
        net_cost_j = self.d[pre_arc_j][arc_i] - self.d[pre_arc_j][arc_j]
        net_cost = net_cost_i + net_cost_j
        return(net_cost)

    def link_routes_alt(self, route_i, i_pos, route_j, j_pos, arc_i, arc_j):
        if i_pos == len(route_i) - 1: 
            return(0)
            post_arc_i = self.depot
        else: post_arc_i = route_i[i_pos + 1]
        if j_pos == len(route_j) - 1: post_arc_j = self.depot
        else: post_arc_j = route_j[j_pos + 1]
        net_cost_i = self.d[arc_i][post_arc_j] - self.d[arc_i][post_arc_i]
        net_cost_j = self.d[arc_j][post_arc_i] - self.d[arc_j][post_arc_j]
        net_cost = net_cost_i + net_cost_j
        return(net_cost)

class remove_insert_CLARPIF():
    
    def __init__(self, info):
        self.info = info
        self.depot = info.depotnewkey
        self.if_cost = info.if_cost_np
        self.d = info.d
        self.depot = info.depotnewkey
        self.dumpCost = info.dumpCost
        self.if_cost = info.if_cost_np

    def check_IF_position_remove(self,  route, position, trip_pre, trip_post):
        if position == 0: 
            pre_arc, pre_IF_flag = trip_pre, True
        else: 
            pre_arc, pre_IF_flag = route[position-1], False
        if position == len(route)-1: 
            post_arc, post_IF_flag = trip_post, True
        else: 
            post_arc, post_IF_flag = route[position+1], False        
        return(pre_arc, post_arc, pre_IF_flag, post_IF_flag)

    def check_IF_position_insert(self, route, position, trip_pre, trip_post):
        if position == 0: 
            pre_arc, pre_IF_flag = trip_pre, True
        else: 
            pre_arc, pre_IF_flag = route[position-1], False
        if position == len(route): 
            post_arc, post_IF_flag = trip_post, True
        else: 
            post_arc, post_IF_flag = route[position], False        
        return(pre_arc, post_arc, pre_IF_flag, post_IF_flag)

    def split_route_cost(self, route, position, trip_pre, trip_post):
        (pre_arc, post_arc, pre_IF_flag, post_IF_flag) = self.check_IF_position_insert(route, position, trip_pre, trip_post)
        if (pre_IF_flag == True)|(post_IF_flag == True): 
            split_cost = self.if_cost[pre_arc][post_arc]
        else: 
            split_cost = self.d[pre_arc][post_arc]
        return(split_cost, pre_arc, post_arc)
    
    def insert_route_cost(self, route, position, arc, trip_pre, trip_post):
        (pre_arc, post_arc, pre_IF_flag, post_IF_flag) = self.check_IF_position_insert(route, position, trip_pre, trip_post)
        if pre_IF_flag:
            insert_cost = self.if_cost[pre_arc][arc] + self.d[arc][post_arc]   
        elif post_IF_flag:
            insert_cost = self.d[pre_arc][arc] + self.if_cost[arc][post_arc]   
        else:
            insert_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]
        return(insert_cost, pre_arc, post_arc)
                
    def remove_from_route(self, route, position, trip_pre, trip_post):
        arc = route[position]
        (pre_arc, post_arc, pre_IF_flag, post_IF_flag) = self.check_IF_position_remove(route, position, trip_pre, trip_post)
        if (pre_IF_flag == True) & (post_IF_flag == True):
            remove_cost = self.if_cost[pre_arc][arc] + self.if_cost[arc][post_arc] - self.dumpCost
            shift_cost = self.if_cost[pre_arc][post_arc]
        if pre_IF_flag:
            remove_cost = self.if_cost[pre_arc][arc] + self.d[arc][post_arc]
            shift_cost = self.if_cost[pre_arc][post_arc]    
        elif post_IF_flag:
            remove_cost = self.d[pre_arc][arc] + self.if_cost[arc][post_arc]
            shift_cost = self.if_cost[pre_arc][post_arc]
        else:
            remove_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]
            shift_cost = self.d[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)
    
    def insert_in_route(self, route, position, arc, trip_pre, trip_post):
        split_cost = self.split_route_cost(route, position, trip_pre, trip_post)[0]
        insert_cost = self.insert_route_cost(route, position, arc, trip_pre, trip_post)[0]
        net_insert_cost = insert_cost - split_cost
        return(net_insert_cost, split_cost, insert_cost)
    
    def replace_in_route(self, route, position, arc, trip_pre, trip_post):
        replace_arc = route[position]
        (pre_arc, post_arc, pre_IF_flag, post_IF_flag) = self.check_IF_position_remove(route, position, trip_pre, trip_post)
        if (pre_IF_flag == True) & (post_IF_flag == True):
            remove_cost = self.if_cost[pre_arc][replace_arc] + self.if_cost[replace_arc][post_arc]
            insert_cost = self.if_cost[pre_arc][arc] + self.if_cost[arc][post_arc]
        elif pre_IF_flag:
            remove_cost = self.if_cost[pre_arc][replace_arc] + self.d[replace_arc][post_arc]
            insert_cost = self.if_cost[pre_arc][arc] + self.d[arc][post_arc]
        elif post_IF_flag:
            remove_cost = self.d[pre_arc][replace_arc] + self.if_cost[replace_arc][post_arc]
            insert_cost = self.d[pre_arc][arc] + self.if_cost[arc][post_arc]
        else:
            remove_cost = self.d[pre_arc][replace_arc] + self.d[replace_arc][post_arc]
            insert_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]                    
        net_replace_cost = insert_cost - remove_cost
        return(net_replace_cost, remove_cost, insert_cost)
    
    def remove_special_1(self, trip_i, trip_j):
        net_remove = self.if_cost[trip_i[-2]][trip_i[-1]] + self.d[trip_i[-1]][trip_j[0]] - self.if_cost[trip_i[-1]][trip_j[0]] - self.d[trip_i[-2]][trip_i[-1]] 
        return(net_remove)

    def remove_special_1b(self, trip_i, trip_j, i_pre, i_t):
        if i_t > 0:
            old_cost = self.if_cost[trip_i[-1]][trip_j[0]]
            new_cost = self.d[trip_i[-1]][trip_j[0]]
        else: 
            old_cost = self.if_cost[trip_i[-1]][trip_j[0]]
            new_cost = self.d[trip_i[-1]][trip_j[0]]
        net_remove = new_cost - old_cost
        return(net_remove)

    def remove_special_2(self, trip_i, trip_j):
        net_remove = self.if_cost[trip_i[0]][trip_i[1]] + self.d[trip_j[-1]][trip_i[0]] - self.if_cost[trip_j[-1]][trip_i[0]] - self.d[trip_i[0]][trip_i[1]]
        return(net_remove)

    def remove_special_2c(self, trip_i, trip_j, j_post):
        old_cost = self.if_cost[trip_i[-1]][trip_j[0]] #+ self.if_cost[trip_j[0]][j_post]
        new_cost = self.d[trip_i[-1]][trip_j[0]] #+ self.if_cost[trip_j[0]][j_post]
        net_remove = new_cost - old_cost
        return(net_remove)
   
    def replace_special(self, trip_i, trip_j):
        old = self.if_cost[trip_i[-1]][trip_j[0]] + self.d[trip_i[-2]][trip_i[-1]] + self.d[trip_j[0]][trip_j[1]] 
        new = self.if_cost[trip_j[0]][trip_i[-1]] + self.d[trip_i[-2]][trip_j[0]] + self.d[trip_i[-1]][trip_j[1]] 
        net_replace = new-old
        return(net_replace)
    
    def replace_special1(self, trip_i, trip_j, i_pre, i_t):
        if i_t > 0:
            old = self.if_cost[i_pre][trip_i[0]] + self.if_cost[trip_i[0]][trip_j[0]] + self.d[trip_j[0]][trip_j[1]]
            new = self.if_cost[i_pre][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[0]] + self.d[trip_i[0]][trip_j[1]]
        else:
            old = self.d[i_pre][trip_i[0]] + self.if_cost[trip_i[0]][trip_j[0]] + self.d[trip_j[0]][trip_j[1]]
            new = self.d[i_pre][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[0]] + self.d[trip_i[0]][trip_j[1]]            
        net_replace = new-old
        return(net_replace)

    def replace_special2(self, trip_i, trip_j, j_post):
        old = self.d[trip_i[-2]][trip_i[-1]] + self.if_cost[trip_i[-1]][trip_j[0]] + self.if_cost[trip_j[0]][j_post]
        new = self.d[trip_i[-2]][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[-1]] + self.if_cost[trip_i[-1]][j_post]
        net_replace = new-old
        return(net_replace)
    
    def replace_special3(self, trip_i, trip_j, i_pre, j_post, i_t):
        if i_t > 0:
            old = self.if_cost[i_pre][trip_i[0]] + self.if_cost[trip_i[0]][trip_j[0]] + self.if_cost[trip_j[0]][j_post]
            new = self.if_cost[i_pre][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[0]] + self.if_cost[trip_i[0]][j_post]
        else:
            old = self.d[i_pre][trip_i[0]] + self.if_cost[trip_i[0]][trip_j[0]] + self.if_cost[trip_j[0]][j_post]
            new = self.d[i_pre][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[0]] + self.if_cost[trip_i[0]][j_post]
        net_replace = new-old
        return(net_replace)

class remove_insert_CLARPIF_2():
    
    def __init__(self, info):
        self.info = info
        self.depot = info.depotnewkey
        self.if_cost = info.if_cost_np
        self.d = info.d
        self.depot = info.depotnewkey
        self.dumpCost = info.dumpCost
        self.if_cost = info.if_cost_np

    def remove_from_route(self, route, position):
        arc = route[position]
        pre_arc, post_arc = route[position - 1], route[position + 1]
        remove_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]
        shift_cost = self.d[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_from_route_double(self, route, position):
        arc = route[position]
        arc2 = route[position + 1]
        pre_arc, post_arc = route[position - 1], route[position + 2]
        remove_cost = self.d[pre_arc][arc] + self.d[arc2][post_arc]
        shift_cost = self.d[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_from_route_pre_if(self, route, position):
        arc = route[position]
        pre_arc, post_arc = route[position - 1], route[position + 2]
        remove_cost = self.d[pre_arc][arc] + self.if_cost[arc][post_arc]
        shift_cost = self.if_cost[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_from_route_pre_if_double(self, route, position):
        arc = route[position]
        arc2 = route[position + 1]
        pre_arc, post_arc = route[position - 1], route[position + 3]
        remove_cost = self.d[pre_arc][arc] + self.if_cost[arc2][post_arc]
        shift_cost = self.if_cost[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_from_route_post_if(self, route, position):
        arc = route[position]
        pre_arc, post_arc = route[position - 2], route[position + 1]
        remove_cost = self.if_cost[pre_arc][arc] + self.d[arc][post_arc]
        shift_cost = self.if_cost[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_from_route_post_if_double(self, route, position):
        arc = route[position]
        arc2 = route[position + 1]
        pre_arc, post_arc = route[position - 2], route[position + 2]
        remove_cost = self.if_cost[pre_arc][arc] + self.d[arc2][post_arc]
        shift_cost = self.if_cost[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_depot_trip_from_route(self, route, position):
        arc = route[position]
        pre_arc, post_arc = route[position - 1], route[position + 2]
        remove_cost = self.d[pre_arc][arc] + self.if_cost[arc][post_arc]
        shift_cost = self.d[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_depot_trip_from_route_double(self, route, position):
        arc = route[position]
        arc2 = route[position + 1]
        pre_arc, post_arc = route[position - 1], route[position + 3]
        remove_cost = self.d[pre_arc][arc] + self.if_cost[arc2][post_arc]
        shift_cost = self.d[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_trip_from_route(self, route, position):
        arc = route[position]
        pre_arc, post_arc = route[position - 2], route[position + 2]
        remove_cost = self.if_cost[pre_arc][arc] + self.if_cost[arc][post_arc]
        shift_cost = self.if_cost[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def remove_trip_from_route_double(self, route, position):
        arc = route[position]
        arc2 = route[position + 1]
        pre_arc, post_arc = route[position - 2], route[position + 3]
        remove_cost = self.if_cost[pre_arc][arc] + self.if_cost[arc2][post_arc]
        shift_cost = self.if_cost[pre_arc][post_arc]             
        net_remove_cost = shift_cost - remove_cost
        return(net_remove_cost, remove_cost, shift_cost)

    def insert_in_route(self, route, position, arc):
        pre_arc, post_arc = route[position - 1], route[position]
        split_cost = self.d[pre_arc][post_arc]
        insert_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]
        net_insert_cost = insert_cost - split_cost
        return(net_insert_cost, split_cost, insert_cost)

    def insert_in_route_double(self, route, position, arc, arc2):
        pre_arc, post_arc = route[position - 1], route[position]
        split_cost = self.d[pre_arc][post_arc]
        insert_cost = self.d[pre_arc][arc] + self.d[arc2][post_arc]
        net_insert_cost = insert_cost - split_cost
        return(net_insert_cost, split_cost, insert_cost)

    def insert_in_route_post_if(self, route, position, arc):
        pre_arc, post_arc = route[position - 2], route[position]
        split_cost = self.if_cost[pre_arc][post_arc]
        insert_cost = self.if_cost[pre_arc][arc] + self.d[arc][post_arc]
        net_insert_cost = insert_cost - split_cost
        return(net_insert_cost, split_cost, insert_cost)

    def insert_in_route_post_if_double(self, route, position, arc, arc2):
        pre_arc, post_arc = route[position - 2], route[position]
        split_cost = self.if_cost[pre_arc][post_arc]
        insert_cost = self.if_cost[pre_arc][arc] + self.d[arc2][post_arc]
        net_insert_cost = insert_cost - split_cost
        return(net_insert_cost, split_cost, insert_cost)

    def insert_in_route_on_if(self, route, position, arc):
        pre_arc, post_arc = route[position - 1], route[position + 1]
        split_cost = self.if_cost[pre_arc][post_arc]
        insert_cost = self.d[pre_arc][arc] + self.if_cost[arc][post_arc]
        net_insert_cost = insert_cost - split_cost
        return(net_insert_cost, split_cost, insert_cost)
 
    def insert_in_route_on_if_double(self, route, position, arc, arc2):
        pre_arc, post_arc = route[position - 1], route[position + 1]
        split_cost = self.if_cost[pre_arc][post_arc]
        insert_cost = self.d[pre_arc][arc] + self.if_cost[arc2][post_arc]
        net_insert_cost = insert_cost - split_cost
        return(net_insert_cost, split_cost, insert_cost)
    
    def replace_in_route_normal(self, route, position, arc):
        pre_arc = route[position - 1]
        post_arc = route[position + 1]
        replace_arc = route[position]
        remove_cost = self.d[pre_arc][replace_arc] + self.d[replace_arc][post_arc]
        insert_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]        
        net_replace = insert_cost - remove_cost
        return(net_replace, remove_cost, insert_cost)

    def replace_in_route_pre_if(self, route, position, arc):
        pre_arc = route[position - 1]
        post_arc = route[position + 2]
        replace_arc = route[position]
        remove_cost = self.d[pre_arc][replace_arc] + self.if_cost[replace_arc][post_arc]
        insert_cost = self.d[pre_arc][arc] + self.if_cost[arc][post_arc]        
        net_replace = insert_cost - remove_cost
        return(net_replace, remove_cost, insert_cost)
        
    def replace_in_route_post_if(self, route, position, arc):
        pre_arc = route[position - 2]
        post_arc = route[position + 1]
        replace_arc = route[position]
        remove_cost = self.if_cost[pre_arc][replace_arc] + self.d[replace_arc][post_arc]
        insert_cost = self.if_cost[pre_arc][arc] + self.d[arc][post_arc]        
        net_replace = insert_cost - remove_cost
        return(net_replace, remove_cost, insert_cost)

    def replace_in_route_single_trip(self, route, position, arc):
        pre_arc = route[position - 2]
        post_arc = route[position + 2]
        replace_arc = route[position]
        remove_cost = self.if_cost[pre_arc][replace_arc] + self.if_cost[replace_arc][post_arc]
        insert_cost = self.if_cost[pre_arc][arc] + self.if_cost[arc][post_arc]        
        net_replace = insert_cost - remove_cost
        return(net_replace, remove_cost, insert_cost)

    def split_route_normal(self, route, position):
        pre_arc = route[position - 1]
        arc = route[position]
        split_cost = self.d[pre_arc][arc]
        return(split_cost)

    def link_route_normal(self, route, position, arc):
        pre_arc = route[position - 1]
        split_cost = self.d[pre_arc][arc]
        return(split_cost)

    def link_route_post_if(self, route, position, arc):
        pre_arc = route[position - 2]
        split_cost = self.if_cost[pre_arc][arc]
        return(split_cost)

    def link_route_if(self, route, position, arc):
        pre_arc = route[position - 1]
        split_cost = self.if_cost[pre_arc][arc]
        return(split_cost)

    def link_route_depot(self, route, position, arc):
        pre_arc = route[position - 1]
        split_cost = self.d[pre_arc][arc]
        return(split_cost)

    def link_route_ifif(self, route, position, arc):
        pre_arc = route[position - 2]
        split_cost = self.if_cost[pre_arc][arc]
        return(split_cost)

    def replace_in_route(self, route, position, arc, trip_pre, trip_post):
        replace_arc = route[position]
        (pre_arc, post_arc, pre_IF_flag, post_IF_flag) = self.check_IF_position_remove(route, position, trip_pre, trip_post)
        if (pre_IF_flag == True) & (post_IF_flag == True):
            remove_cost = self.if_cost[pre_arc][replace_arc] + self.if_cost[replace_arc][post_arc]
            insert_cost = self.if_cost[pre_arc][arc] + self.if_cost[arc][post_arc]
        elif pre_IF_flag:
            remove_cost = self.if_cost[pre_arc][replace_arc] + self.d[replace_arc][post_arc]
            insert_cost = self.if_cost[pre_arc][arc] + self.d[arc][post_arc]
        elif post_IF_flag:
            remove_cost = self.d[pre_arc][replace_arc] + self.if_cost[replace_arc][post_arc]
            insert_cost = self.d[pre_arc][arc] + self.if_cost[arc][post_arc]
        else:
            remove_cost = self.d[pre_arc][replace_arc] + self.d[replace_arc][post_arc]
            insert_cost = self.d[pre_arc][arc] + self.d[arc][post_arc]                    
        net_replace_cost = insert_cost - remove_cost
        return(net_replace_cost, remove_cost, insert_cost)
    
    def remove_special_1(self, trip_i, trip_j):
        net_remove = self.if_cost[trip_i[-2]][trip_i[-1]] + self.d[trip_i[-1]][trip_j[0]] - self.if_cost[trip_i[-1]][trip_j[0]] - self.d[trip_i[-2]][trip_i[-1]] 
        return(net_remove)

    def remove_special_1b(self, trip_i, trip_j, i_pre, i_t):
        if i_t > 0:
            old_cost = self.if_cost[trip_i[-1]][trip_j[0]]
            new_cost = self.d[trip_i[-1]][trip_j[0]]
        else: 
            old_cost = self.if_cost[trip_i[-1]][trip_j[0]]
            new_cost = self.d[trip_i[-1]][trip_j[0]]
        net_remove = new_cost - old_cost
        return(net_remove)

    def remove_special_2(self, trip_i, trip_j):
        net_remove = self.if_cost[trip_i[0]][trip_i[1]] + self.d[trip_j[-1]][trip_i[0]] - self.if_cost[trip_j[-1]][trip_i[0]] - self.d[trip_i[0]][trip_i[1]]
        return(net_remove)

    def remove_special_2c(self, trip_i, trip_j, j_post):
        old_cost = self.if_cost[trip_i[-1]][trip_j[0]] #+ self.if_cost[trip_j[0]][j_post]
        new_cost = self.d[trip_i[-1]][trip_j[0]] #+ self.if_cost[trip_j[0]][j_post]
        net_remove = new_cost - old_cost
        return(net_remove)
   
    def replace_special(self, trip_i, trip_j):
        old = self.if_cost[trip_i[-1]][trip_j[0]] + self.d[trip_i[-2]][trip_i[-1]] + self.d[trip_j[0]][trip_j[1]] 
        new = self.if_cost[trip_j[0]][trip_i[-1]] + self.d[trip_i[-2]][trip_j[0]] + self.d[trip_i[-1]][trip_j[1]] 
        net_replace = new-old
        return(net_replace)
    
    def replace_special1(self, trip_i, trip_j, i_pre, i_t):
        if i_t > 0:
            old = self.if_cost[i_pre][trip_i[0]] + self.if_cost[trip_i[0]][trip_j[0]] + self.d[trip_j[0]][trip_j[1]]
            new = self.if_cost[i_pre][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[0]] + self.d[trip_i[0]][trip_j[1]]
        else:
            old = self.d[i_pre][trip_i[0]] + self.if_cost[trip_i[0]][trip_j[0]] + self.d[trip_j[0]][trip_j[1]]
            new = self.d[i_pre][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[0]] + self.d[trip_i[0]][trip_j[1]]            
        net_replace = new-old
        return(net_replace)

    def replace_special2(self, trip_i, trip_j, j_post):
        old = self.d[trip_i[-2]][trip_i[-1]] + self.if_cost[trip_i[-1]][trip_j[0]] + self.if_cost[trip_j[0]][j_post]
        new = self.d[trip_i[-2]][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[-1]] + self.if_cost[trip_i[-1]][j_post]
        net_replace = new-old
        return(net_replace)
    
    def replace_special3(self, trip_i, trip_j, i_pre, j_post, i_t):
        if i_t > 0:
            old = self.if_cost[i_pre][trip_i[0]] + self.if_cost[trip_i[0]][trip_j[0]] + self.if_cost[trip_j[0]][j_post]
            new = self.if_cost[i_pre][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[0]] + self.if_cost[trip_i[0]][j_post]
        else:
            old = self.d[i_pre][trip_i[0]] + self.if_cost[trip_i[0]][trip_j[0]] + self.if_cost[trip_j[0]][j_post]
            new = self.d[i_pre][trip_j[0]] + self.if_cost[trip_j[0]][trip_i[0]] + self.if_cost[trip_i[0]][j_post]
        net_replace = new-old
        return(net_replace)
        
 