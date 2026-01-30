class Solution:
    def specialNodes(self, n: int, edges: List[List[int]], x: int, y: int, z: int) -> int:
        # 构造树的邻接表
        adj = [[] for _ in range(n)] # 0~n-1
        for a,b in map(tuple,edges):
            adj[a].append(b)
            adj[b].append(a)

        print(adj)
        
        # 以 0 节点为根，求每个节点的深度和父节点
        depth = [0] + [n]*(n-1) # n 个节点的最大深度<=n
        parent = [-1]*n
        q0 = [0]
        while q0: # 层序遍历法
            q1 = []
            for p in q0:
                for son in adj[p]:
                    # 关键！确保不是 子 -> 父
                    if depth[son] > depth[p]:
                        depth[son] = depth[p] +1
                        parent[son] = p
                        q1.append(son)
            q0 = q1

        print(depth)
        print(parent)

        # 最近公共祖先
        def com_ac(a,b):
            nonlocal depth, parent
            if depth[a] > depth[b]:
                a, b = b, a 
            while depth[a] < depth[b]:
                b = parent[b]
            while a!=b:
                a=parent[a]
                b=parent[b]
            return a 

        # 任意两节点距离
        def dis(a,b):
            nonlocal depth, parent
            p = com_ac(a,b)
            return depth[a]+depth[b]-2*depth[p]
        
        a n Sfor u in range(n) ：dxyz2sorted(dis(u,a)**2 for a inif dxyz2[Ø]+dxyz2[1]dxyz2 [ 2 ]：a n S 十= 1a n S（ x ， Y ， z 月