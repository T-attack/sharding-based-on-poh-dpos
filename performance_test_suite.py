import asyncio
import time
from typing import Dict, List
from performance_test import PerformanceTester

class TestScenario:
    def __init__(self, name: str, tx_count: int, batch_size: int, validator_count: int):
        self.name = name
        self.tx_count = tx_count
        self.batch_size = batch_size
        self.validator_count = validator_count

class PerformanceTestSuite:
    def __init__(self):
        self.scenarios = [
            # 基准测试
            TestScenario("基准测试", 1000, 100, 21),
            
            # 高TPS测试
            TestScenario("高TPS测试", 5000, 500, 21),
            
            # 大规模验证者测试
            TestScenario("大规模验证者", 1000, 100, 50),
            
            # 小批量交易测试
            TestScenario("小批量交易", 1000, 10, 21),
            
            # 压力测试
            TestScenario("压力测试", 10000, 1000, 21),
        ]
        self.results: Dict[str, dict] = {}

    async def run_all_tests(self):
        print("开始性能测试套件...")
        total_scenarios = len(self.scenarios)
        
        for i, scenario in enumerate(self.scenarios, 1):
            print(f"\n[{i}/{total_scenarios}] 执行测试场景: {scenario.name}")
            print(f"参数: 交易数={scenario.tx_count}, 批次大小={scenario.batch_size}, 验证者数={scenario.validator_count}")
            
            tester = PerformanceTester(
                transaction_count=scenario.tx_count,
                batch_size=scenario.batch_size,
                validator_count=scenario.validator_count
            )
            
            # 运行测试并收集结果
            start_time = time.time()
            await tester.run_test()
            duration = time.time() - start_time
            
            # 保存结果
            self.results[scenario.name] = {
                "duration": duration,
                "params": {
                    "tx_count": scenario.tx_count,
                    "batch_size": scenario.batch_size,
                    "validator_count": scenario.validator_count
                },
                "metrics": tester.get_metrics()
            }
            
            print(f"\n场景 {scenario.name} 完成 ({i}/{total_scenarios})")
            print(f"耗时: {duration:.2f} 秒")
            
            if i < total_scenarios:
                print("系统冷却中...")
                for j in range(5, 0, -1):
                    print(f"\r休息 {j} 秒", end="")
                    await asyncio.sleep(1)
                print("\r" + " " * 20 + "\r", end="")  # 清除倒计时
            
        self.print_summary()

    def print_summary(self):
        print("\n=== 性能测试套件总结 ===")
        print("\n各场景性能比较:")
        
        # 创建比较表格
        headers = ["场景", "TPS", "平均延迟(ms)", "CPU使用率(%)", "内存(MB)"]
        rows = []
        
        for name, result in self.results.items():
            metrics = result["metrics"]
            rows.append([
                name,
                f"{metrics['tps']:.2f}",
                f"{metrics['average_latency']*1000:.2f}",
                f"{metrics['avg_cpu_usage']:.2f}",
                f"{metrics['avg_memory_usage']:.2f}"
            ])
        
        # 打印表格
        self._print_table(headers, rows)
        
        # 输出建议
        print("\n性能优化建议:")
        self._generate_recommendations()

    def _print_table(self, headers: List[str], rows: List[List[str]]):
        # 计算每列的最大宽度
        widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
        
        # 打印表头
        header = " | ".join(f"{h:<{w}}" for h, w in zip(headers, widths))
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        
        # 打印数据行
        for row in rows:
            print(" | ".join(f"{cell:<{w}}" for cell, w in zip(row, widths)))
        print("-" * len(header))

    def _generate_recommendations(self):
        # 分析结果并生成优化建议
        max_tps = max(r["metrics"]["tps"] for r in self.results.values())
        max_tps_scenario = next(name for name, r in self.results.items() 
                              if r["metrics"]["tps"] == max_tps)
        
        print(f"1. 最佳TPS配置在 '{max_tps_scenario}' 场景中实现")
        
        # 分析批次大小的影响
        small_batch = self.results["小批量交易"]["metrics"]["tps"]
        large_batch = self.results["高TPS测试"]["metrics"]["tps"]
        if large_batch > small_batch:
            print("2. 增加批次大小可以提高TPS，建议优化批处理机制")
        else:
            print("2. 小批量处理表现更好，建议关注单笔交易处理效率")
        
        # 分析验证者数量的影响
        base_tps = self.results["基准测试"]["metrics"]["tps"]
        large_validator_tps = self.results["大规模验证者"]["metrics"]["tps"]
        if large_validator_tps < base_tps * 0.8:
            print("3. 验证者数量增加显著影响性能，建议优化共识机制")

async def main():
    suite = PerformanceTestSuite()
    await suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 