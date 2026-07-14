# 如果使用者輸入不明確，引導他正確的用法
from apps.features.self_introduction import self_introduction


def unknown():
    
    text = '''
    我只是一個虛擬的助理，不明白你想說什麼，請說得更明確一點
    --------------------
    '''

    introduction = self_introduction()
    
    return text + introduction
