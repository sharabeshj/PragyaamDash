import numpy as np
import random
from collections import defaultdict

color_choices = ["#3e95cd", "#8e5ea2","#3cba9f","#e8c3b9","#c45850","#66FF66","#FB4D46", "#00755E", "#FFEB00", "#FF9933"]
def createGraphData(df_group, graph_type, X_field, Y_field,labels, group_by = '',op_mode = ''):
    data = []
    if(graph_type == 'bar'):
        if(op_mode == 'group_by'):
            op_dict = defaultdict(lambda: defaultdict(int))
            for x in df_group.groupby([group_by]).groups.keys():
                        
                curr = np.array(df_group[[X_field,Y_field,group_by]])
                for c in curr:
                    op_dict[c[2]][c[0]] = c[1]
                    
            colors=[]
            colors.extend([random.choice(color_choices) for _ in range(len(df_group.groupby([group_by]).groups.keys()))])

            for group in op_dict.keys():        

                color_chosen = random.choice(colors)    

                new_add = []
                for x in data['labels']:
                    new_add.append(op_dict[group][x])
                data.append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                if len(colors) > 1:
                    colors.remove(color_chosen)

        else:
            pass
    
    return data