import numpy as np
import pandas as pd
import math

def compute_mu_sigma(EX, EX2):
    """
    根据对数正态分布的一阶矩 EX 和二阶矩 EX2 计算参数 mu 和 sigma。
    公式：
        sigma^2 = ln(EX2 / EX^2)
        mu = ln(EX) - sigma^2 / 2
    """
    if EX <= 0 or EX2 <= 0:
        raise ValueError("EX 和 EX2 必须为正数")
    ex_sq = EX * EX
    if EX2 <= ex_sq:
        raise ValueError("EX2 必须大于 EX^2，否则方差非正")
    sigma_sq = math.log(EX2 / ex_sq)
    sigma = math.sqrt(sigma_sq)
    mu = math.log(EX) - sigma_sq / 2.0
    return mu, sigma

# ========== 配置区域 ==========
# 定义多组 (EX, EX2) 组合，例如：
# - 小规模 O(n) 期望 10，O(n^2) 期望 200
# - 中等规模 O(n) 期望 100，O(n^2) 期望 20000
# - 大规模 O(n) 期望 500，O(n^2) 期望 500000
param_combos = [
    (ex,q*ex*ex)
    for ex in (5,10,20,50,100)
    for q in (1.5,2,5,10,20,50,100)
]

case_num = 1000000          # 每组生成的样本数量
random_seed = 42          # 固定随机种子保证可重复
np.random.seed(random_seed)
# ==============================

results = []

for EX, EX2 in param_combos:
    # 1. 计算理论 mu, sigma
    mu, sigma = compute_mu_sigma(EX, EX2)
    
    # 2. 生成对数正态分布样本 (numpy 的 lognormal 参数为 mean=mu, sigma=sigma)
    samples = np.random.lognormal(mean=mu, sigma=sigma, size=case_num)
    
    # 3. 排序（可选，仅用于后续规模递增需求，对统计量无影响）
    samples.sort()
    
    # 4. 计算样本统计量
    sample_mean = np.mean(samples)
    sample_mean_sq = np.mean(samples ** 2)   # 二阶矩的样本估计
    
    # 5. 相对误差 (%)
    rel_err_mean = abs(sample_mean - EX) / EX * 100
    rel_err_m2 = abs(sample_mean_sq - EX2) / EX2 * 100
    
    # 保存结果
    results.append({
        "EX": EX,
        "EX2": EX2,
        "mu": mu,
        "sigma": sigma,
        "sample_mean": sample_mean,
        "sample_mean_sq": sample_mean_sq,
        "rel_err_mean (%)": rel_err_mean,
        "rel_err_m2 (%)": rel_err_m2,
    })

# 使用 pandas 展示汇总表格
df = pd.DataFrame(results)
print("对数正态分布参数反演与样本验证结果")
print("=" * 60)
print(df.to_string(index=False, float_format="%.6f"))