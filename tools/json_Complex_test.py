import json
from json import JSONEncoder
class ComplexEncoder(JSONEncoder):
    
    def default(self, o):
        if isinstance(z, complex):
            return {z.__class__.__name__: True, "real":z.real, "imag":z.imag}
        # 让基类的默认方法处理其他对象或引发TypeError
        return JSONEncoder.default(self, o)
    
z = 5 + 9j
zJSON = json.dumps(z, cls=ComplexEncoder)
print(zJSON)
# 或者直接使用编码器
zJson = ComplexEncoder().encode(z)
print(zJSON)