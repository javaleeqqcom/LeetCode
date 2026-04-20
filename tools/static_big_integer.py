import dataclasses
visit_index_vector = []

_CPU_BIT_LEN = 64 # 模拟 size_t 类型（64位系统）

@dataclasses
class BitNumStatic:
    small:int = 0  # 小端
    bitLen:int = 0 # 注意是比特位数
    pre:int = -1   # 高位索引
    # 新建只能是 size_t 以内的数

    @classmethod
    def new(cls, num:int) -> BitNumStatic:
        assert 0<num<(1<<_CPU_BIT_LEN) # 特别地，禁用 0 作为值，首先堆索引不存在 0 ，其次会与是否需要新建节点逻辑重合，导致代码复杂度上升
        return BitNumStatic(num,num.bit_length(),-1)
    
    @classmethod
    def lshift(cls, index:int)-> BitNumStatic: # 用于堆索引的左移操作
        this = visit_index_vector[index]
        if 0 == this.bitLen % _CPU_BIT_LEN: # 因为 bitLen 禁用 0 的状态，因此满了就是整除
            return BitNumStatic(0,this.bitLen+1,index) # 这里的 0 不是真的 0，因为有高位
        else:
            return BitNumStatic(this.small<<1,this.bitLen+1,this.pre)

    @classmethod
    def or1(cls, index:int)-> BitNumStatic:    # 用 |1 代替 +1 （因为总是伴随着 *2+1）
        this = visit_index_vector[index]
        return BitNumStatic(this.small|1,this.bitLen,this.pre)

