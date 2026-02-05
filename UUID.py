import uuid
# 生成一个随机的UUID (最常用)
from collections import Counter
import re
C = Counter()
for i in range(1000):
    unique_id = uuid.uuid4().hex
    if re.match(r"^[0-9a-f]+$",unique_id):
        C[len(unique_id)] += 1
print(C)

s = tuple(range(10))
import json
jstr = json.dumps(s)
print(jstr)