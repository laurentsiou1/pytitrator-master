"""Functions in link with display"""

def state2Text(state,type): 
    """Suivi des états des électrovannes"""
    if state==True: 
        if type=='dispenser': # boitier seringue
            text='DISPENSE'
        elif type=='circuit entrance': 
            text='WATER'
        elif type=='circuit exit':
            text='BIN'
    else:
        if type=='dispenser':
            text='BOTTLE'
        elif type=='circuit entrance':
            text='IN'
        elif type=='circuit exit':
            text='OUT'
    return text