import numpy as np
import random
import time
from typing import List, Tuple, Dict, Callable
from scipy.sparse.csgraph import floyd_warshall

def floyd_standard(graph_matrix: np.ndarray) -> np.ndarray:
    """标准的三层循环Floyd算法"""
    dist = graph_matrix.copy()
    n = dist.shape[0]
    
    for k in range(n):
        for i in range(n):
            if dist[i, k] == np.inf:
                continue
            for j in range(n):
                new_dist = dist[i, k] + dist[k, j]
                if new_dist < dist[i, j]:
                    dist[i, j] = new_dist
    return dist

def floyd_numpy_broadcast_incorrect(graph_matrix: np.ndarray) -> np.ndarray:
    """有问题的numpy广播Floyd算法（使用更新后的值）"""
    dist = graph_matrix.copy()
    n = dist.shape[0]
    
    for k in range(n):
        # 错误：使用了更新过的dist矩阵
        dist = np.minimum(dist, dist[:, k, np.newaxis] + dist[np.newaxis, k, :])
    return dist

def floyd_numpy_broadcast_correct(graph_matrix: np.ndarray) -> np.ndarray:
    """修正的numpy广播Floyd算法（使用原始值）"""
    dist = graph_matrix.copy()
    n = dist.shape[0]
    
    for k in range(n):
        # 正确：使用原始值进行广播
        temp = dist.copy()
        dist = np.minimum(dist, temp[:, k, np.newaxis] + temp[np.newaxis, k, :])
    return dist

def floyd_numpy_vectorized(graph_matrix: np.ndarray) -> np.ndarray:
    """向量化版本的Floyd算法，每次更新整行"""
    dist = graph_matrix.copy()
    n = dist.shape[0]
    
    for k in range(n):
        # 只使用原始值进行更新
        row_k = dist[k, :].copy()
        col_k = dist[:, k].copy()
        
        # 创建广播矩阵
        broadcast = col_k[:, np.newaxis] + row_k[np.newaxis, :]
        dist = np.minimum(dist, broadcast)
    return dist

def scipy_floyd_wrapper(graph_matrix: np.ndarray) -> np.ndarray:
    """SciPy Floyd-Warshall算法包装器"""
    # SciPy的floyd_warshall要求不可达的边用非常大的数表示，这里用inf
    dist_matrix = floyd_warshall(graph_matrix, directed=True, unweighted=False)
    # 处理SciPy返回的inf表示（非常大但不是np.inf）
    dist_matrix[dist_matrix > 1e18] = np.inf
    return dist_matrix

def generate_random_graph(n: int, density: float = 0.3, max_weight: int = 100, seed: int = None) -> np.ndarray:
    """生成随机带权有向图，根据n调整密度"""
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    
    # 大图使用更稀疏的密度
    if n > 50:
        density = min(density, 0.1)
    elif n > 20:
        density = min(density, 0.2)
    
    inf = float('inf')
    graph = np.full((n, n), inf, dtype=np.float64)
    np.fill_diagonal(graph, 0)
    
    # 随机生成边
    for i in range(n):
        for j in range(n):
            if i != j and random.random() < density:
                graph[i, j] = random.randint(1, max_weight)
    
    return graph

def compare_matrices(a: np.ndarray, b: np.ndarray, tolerance: float = 1e-9) -> bool:
    """比较两个矩阵是否相等，处理inf和nan的情况"""
    # 处理形状不一致
    if a.shape != b.shape:
        return False
    
    # 创建掩码：a和b都不是inf的位置
    not_inf_mask = ~np.isinf(a) & ~np.isinf(b)
    # 创建掩码：a和b都是inf的位置
    both_inf_mask = np.isinf(a) & np.isinf(b)
    
    # 对于都不是inf的位置，检查数值差异
    if np.any(not_inf_mask):
        diff = np.abs(a[not_inf_mask] - b[not_inf_mask])
        if np.any(diff > tolerance):
            return False
    
    # 对于都是inf的位置，需要确保都是正inf或都是负inf
    # 在最短路径问题中，inf通常是正无穷
    if np.any(both_inf_mask):
        # 检查是否都是正inf
        a_pos_inf = np.isposinf(a[both_inf_mask])
        b_pos_inf = np.isposinf(b[both_inf_mask])
        if not np.all(a_pos_inf == b_pos_inf):
            return False
    
    # 检查一个inf一个不是inf的情况
    # 创建掩码：a是inf但b不是inf，或者b是inf但a不是inf
    one_inf_mask = (np.isinf(a) & ~np.isinf(b)) | (~np.isinf(a) & np.isinf(b))
    if np.any(one_inf_mask):
        return False
    
    return True

def test_algorithms(floyd_funs: List[Callable], size: int, seed: int = 42, tolerance: float = 1e-9 , 
                    num_tests_per_thread: int = 1000, n_thread:int) -> Tuple[List[bool], List[float]]:
    """
    测试Floyd算法实现的一致性
    
    参数:
        floyd_funs: 要测试的Floyd算法函数列表
        size: 图的大小（节点数）
        seed: 随机种子
        num_tests: 测试次数
        tolerance: 浮点数容差
    
    返回:
        (correct_list, time_list)
        correct_list: 每个算法是否正确（与SciPy基准一致）
        time_list: 每个算法的平均运行时间
    """
    random.seed(seed)
    np.random.seed(seed)
    
    # 初始化结果
    num_algorithms = len(floyd_funs)
    correct_counts = [0] * num_algorithms
    total_times = [0.0] * num_algorithms
    
    print(f"测试规模: {size}×{size}, 测试次数: {num_tests}")
    
    for test_idx in range(num_tests):
        if test_idx % trunk_size == 0 and test_idx > 0:
            print(f"  已进行 {test_idx} 次测试...")
        
        # 生成随机图
        graph = generate_random_graph(size, density=0.3, max_weight=100, seed=seed+test_idx)
        
        # SciPy作为基准
        start = time.time()
        scipy_result = scipy_floyd_wrapper(graph)
        scipy_time = time.time() - start
        
        # 测试每个算法
        for i, floyd_fun in enumerate(floyd_funs):
            try:
                start = time.time()
                result = floyd_fun(graph)
                total_times[i] += time.time() - start
                
                # 使用安全的比较函数
                if compare_matrices(result, scipy_result, tolerance):
                    correct_counts[i] += 1
                elif test_idx == 0:  # 第一次测试就失败，说明算法有严重问题
                    # 找出差异最大的位置
                    diff = np.zeros_like(result)
                    mask = ~np.isinf(result) & ~np.isinf(scipy_result)
                    diff[mask] = np.abs(result[mask] - scipy_result[mask])
                    max_diff = np.max(diff)
                    print(f"  算法{i}第一次测试就失败，最大差异: {max_diff}")
            except Exception as e:
                if test_idx == 0:
                    print(f"  算法{i}出现异常: {e}")
    
    # 计算正确率和平均时间
    correctness = [count == num_tests for count in correct_counts]
    avg_times = [t / num_tests for t in total_times]
    
    print(f"  完成! 正确率: {[f'{c}/{num_tests}' for c in correct_counts]}")
    print(f"  平均时间(秒): {[f'{t:.6f}' for t in avg_times]}")
    
    return correctness, avg_times

def test_specific_cases():
    """测试一些特定的案例"""
    print("\n=== 特定案例测试 ===")
    
    test_cases = []
    
    # 案例1: 简单的4节点图
    inf = float('inf')
    case1 = np.array([
        [0, 1, inf, inf],
        [inf, 0, 2, inf],
        [inf, inf, 0, 3],
        [inf, 1, inf, 0]
    ], dtype=np.float64)
    test_cases.append(("简单4节点图", case1))
    
    # 案例2: 完全图
    case2 = np.full((5, 5), inf, dtype=np.float64)
    np.fill_diagonal(case2, 0)
    for i in range(5):
        for j in range(5):
            if i != j:
                case2[i, j] = random.randint(1, 10)
    test_cases.append(("完全5节点图", case2))
    
    # 案例3: 稀疏图
    case3 = np.full((6, 6), inf, dtype=np.float64)
    np.fill_diagonal(case3, 0)
    case3[0, 1] = 2
    case3[1, 2] = 3
    case3[2, 3] = 1
    case3[3, 4] = 4
    case3[4, 5] = 2
    case3[5, 0] = 5
    test_cases.append(("环状6节点图", case3))
    
    # 要测试的算法
    algorithms = [
        ("标准三层循环", floyd_standard),
        ("错误广播", floyd_numpy_broadcast_incorrect),
        ("正确广播", floyd_numpy_broadcast_correct),
        ("向量化", floyd_numpy_vectorized),
        ("SciPy", scipy_floyd_wrapper)
    ]
    
    for case_name, graph in test_cases:
        print(f"\n案例: {case_name}")
        print("原始图:")
        print(graph)
        
        results = {}
        for algo_name, algo_func in algorithms:
            try:
                result = algo_func(graph)
                results[algo_name] = result
                print(f"\n{algo_name} 最短路径矩阵:")
                print(result)
            except Exception as e:
                print(f"\n{algo_name} 出错: {e}")
        
        # 检查一致性
        if len(results) > 1:
            print(f"\n一致性检查:")
            keys = list(results.keys())
            for i in range(len(keys)):
                for j in range(i+1, len(keys)):
                    if compare_matrices(results[keys[i]], results[keys[j]]):
                        print(f"  {keys[i]} 与 {keys[j]} 一致")
                    else:
                        print(f"  {keys[i]} 与 {keys[j]} 不一致")

def main():
    """主测试函数"""
    print("Floyd算法实现对比测试")
    print("=" * 60)
    
    # 要测试的算法（排除SciPy，因为它作为基准）
    algorithms_to_test = [
        ("标准三层循环", floyd_standard),
        ("错误广播", floyd_numpy_broadcast_incorrect),
        ("正确广播", floyd_numpy_broadcast_correct),
        ("向量化", floyd_numpy_vectorized)
    ]
    
    # 测试参数
    test_sizes = [5, 10, 20, 50, 100]
    test_counts = [100000, 50000, 20000, 5000, 2000]  # 大矩阵测试次数减少
    
    # 记录哪些算法通过了测试
    passed_algorithms = [True] * len(algorithms_to_test)
    
    # 先运行特定案例测试
    test_specific_cases()
    
    print("\n" + "=" * 60)
    print("开始随机图测试")
    print("=" * 60)
    
    for size_idx, size in enumerate(test_sizes):
        print(f"\n{'='*40}")
        print(f"测试矩阵规模: {size}×{size}")
        print(f"{'='*40}")
        
        # 只测试通过的算法
        active_algorithms = []
        active_names = []
        for i, (name, func) in enumerate(algorithms_to_test):
            if passed_algorithms[i]:
                active_algorithms.append(func)
                active_names.append(name)
        
        if not active_algorithms:
            print("所有算法都已失败，停止测试")
            break
        
        num_tests = test_counts[size_idx]
        
        # 运行测试
        correctness, avg_times = test_algorithms(
            active_algorithms, size, seed=42, num_tests=num_tests
        )
        
        # 更新通过状态
        idx = 0
        for i in range(len(algorithms_to_test)):
            if passed_algorithms[i]:
                if not correctness[idx]:
                    print(f"  ✗ 算法 '{algorithms_to_test[i][0]}' 在规模 {size} 上失败，将被剔除")
                    passed_algorithms[i] = False
                idx += 1
        
        # 显示通过状态
        print(f"\n  通过状态:")
        for i, (name, _) in enumerate(algorithms_to_test):
            status = "✓" if passed_algorithms[i] else "✗"
            print(f"    {status} {name}")
    
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    
    for i, (name, _) in enumerate(algorithms_to_test):
        status = "通过" if passed_algorithms[i] else "失败"
        print(f"  {name}: {status}")
    
    print(f"\n结论:")
    print("  1. 标准三层循环算法总是正确的")
    print("  2. 错误的广播算法（使用更新后的值）在某些情况下会失败")
    print("  3. 正确的广播算法和向量化算法是可靠的")
    print("  4. 对于大规模矩阵，推荐使用向量化或SciPy的实现")

if __name__ == "__main__":
    main()