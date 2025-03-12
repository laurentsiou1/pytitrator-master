"""Functions in link with display"""

def state2Text(state,type):
    if state==True: 
        if type=='dispenser':
            text='ON'
        elif type=='circuit entrance':
            text='WATER'
        elif type=='circuit exit':
            text='BIN'
    else:
        if type=='dispenser':
            text='OFF'
        elif type=='circuit entrance':
            text='IN'
        elif type=='circuit exit':
            text='OUT'
    return text