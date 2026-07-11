# 如果使用者輸入不明確，引導他正確的用法
from apps.features.self_introduction import self_introduction


def unknown():
    
    text = '''
    我不明白你在說什麼
    
    --------------------

    '''

    introduction = self_introduction
    
    return text + introduction
