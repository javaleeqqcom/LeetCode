class _meta_random:
    pass

class _list_random(_meta_random):
    pass

obj = _list_random()
print(isinstance(obj, _meta_random))  # 输出: True