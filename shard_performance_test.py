import asyncio
import time
import random
from dataclasses import dataclass
from typing import Dict, List, Set
from time_sharding import TimeShardingManager
from transaction_router import TransactionRouter, Transaction
from cross_shard import CrossShardManager
from state_sync import StateSyncManager
from network import P2PNetwork
from poh import ProofOfHistory
from dpos import DPOS, ConsensusSystem
import psutil
import os

@dataclass
class ShardTestScenario:
    """分片测试场景"""
    name: str                    # 场景名称
    tx_count: int               # 总交易数
    batch_size: int             # 批次大小
    validator_count: int        # 验证者总数
    shard_count: int            # 分片数量
    cross_shard_ratio: float    # 跨分片交易比例 (0-1)

class ShardPerformanceTester:
    def __init__(self):
        self.scenarios = [
            # 基准测试
            ShardTestScenario("基准测试", 1000, 100, 21, 4, 0.1),
            
            # 高TPS测试
            ShardTestScenario("高TPS测试", 5000, 500, 21, 4, 0.1),
            
            # 大规模验证者测试
            ShardTestScenario("大规模验证者", 1000, 100, 50, 4, 0.1),
            
            # 小批量交易测试
            ShardTestScenario("小批量交易", 1000, 10, 21, 4, 0.1),
            
            # 压力测试
            ShardTestScenario("压力测试", 10000, 1000, 21, 4, 0.1),
            
            # 分片特定测试
            ShardTestScenario("高跨分片", 1000, 100, 21, 4, 0.4),
            ShardTestScenario("大规模分片", 1000, 100, 40, 8, 0.2),
        ]
        self.results: Dict[str, dict] = {}
        self.process = psutil.Process(os.getpid())
        self.network_latency = 0.01  # 10ms网络延迟
        self.processing_latency = 0.001  # 1ms处理延迟
        self.consensus_latency = 0.005  # 5ms共识延迟

    def collect_system_metrics(self) -> tuple[float, float]:
        """收集系统指标"""
        cpu_percent = self.process.cpu_percent()
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        return cpu_percent, memory_mb

    async def simulate_network_delay(self):
        """模拟网络延迟"""
        await asyncio.sleep(self.network_latency * random.uniform(0.5, 1.5))

    async def simulate_processing_delay(self):
        """模拟处理延迟"""
        await asyncio.sleep(self.processing_latency * random.uniform(0.8, 1.2))

    async def simulate_consensus_delay(self):
        """模拟共识延迟"""
        await asyncio.sleep(self.consensus_latency * random.uniform(0.9, 1.1))

    def run_scenario(self, scenario: ShardTestScenario):
        """运行单个测试场景"""
        print(f"\n执行场景: {scenario.name}")
        print(f"参数: 交易数={scenario.tx_count}, 批次={scenario.batch_size}, "
              f"验证者={scenario.validator_count}, 分片数={scenario.shard_count}, "
              f"跨分片率={scenario.cross_shard_ratio:.1%}")

        try:
            metrics = {
                "latencies": [],
                "cross_shard_latencies": [],
                "tps_samples": [],
                "cpu_samples": [],
                "memory_samples": []
            }
            
            # 初始化组件
            network = P2PNetwork()
            time_sharding = TimeShardingManager(
                slot_duration=2,
                shard_count=scenario.shard_count,
                validators_per_shard=scenario.validator_count // scenario.shard_count
            )
            
            cross_shard = CrossShardManager(time_sharding, network)
            tx_router = TransactionRouter(time_sharding, cross_shard)
            
            # 初始化共识系统（每个分片一个）
            poh = ProofOfHistory(difficulty=3)
            dpos = DPOS(max_validators=scenario.validator_count)
            consensus_systems = {
                shard_id: ConsensusSystem(poh, dpos, shard_id)
                for shard_id in range(scenario.shard_count)
            }
            
            # 初始化验证者
            validators = [f"validator_{i}" for i in range(scenario.validator_count)]
            time_sharding.initialize_shards(validators)
            for validator in validators:
                dpos.stake(validator, 1000)
                dpos.register_validator(validator)
                
            # 开始测试
            start_time = time.time()
            total_transactions = 0
            processed_tx = 0
            batch_tx_count = 0
            last_metrics_time = time.time()
            
            while processed_tx < scenario.tx_count:
                batch_start = time.time()
                batch_tx_count = 0
                
                # 生成和处理交易
                for _ in range(min(scenario.batch_size, scenario.tx_count - processed_tx)):
                    self.simulate_processing_delay()
                    
                    is_cross_shard = random.random() < scenario.cross_shard_ratio
                    from_shard = random.randint(0, scenario.shard_count - 1)
                    to_shard = (from_shard + 1) % scenario.shard_count if is_cross_shard else from_shard
                    
                    tx = Transaction(
                        tx_id=f"tx_{time.time()}_{processed_tx}",
                        from_shard=from_shard,
                        to_shard=to_shard,
                        data={"amount": random.randint(1, 1000)}
                    )
                    
                    tx_start = time.time()
                    tx_router.route_transaction(tx)
                    latency = time.time() - tx_start
                    
                    if is_cross_shard:
                        metrics["cross_shard_latencies"].append(latency)
                    else:
                        metrics["latencies"].append(latency)
                        
                    batch_tx_count += 1
                    processed_tx += 1
                    total_transactions += 1
                
                # 处理每个分片的交易
                for shard_id in range(scenario.shard_count):
                    self.simulate_consensus_delay()
                    validator = dpos.get_next_block_validator()
                    shard_txs = tx_router.process_shard_transactions(shard_id)
                    if shard_txs:
                        consensus_systems[shard_id].create_block(validator, shard_txs)
                
                # 计算批次TPS
                batch_time = time.time() - batch_start
                if batch_time > 0 and batch_tx_count > 0:
                    batch_tps = batch_tx_count / batch_time
                    metrics["tps_samples"].append(batch_tps)
                
                # 收集系统指标
                cpu, mem = self.collect_system_metrics()
                metrics["cpu_samples"].append(cpu)
                metrics["memory_samples"].append(mem)
                
                print(f"\r进度: {processed_tx}/{scenario.tx_count} 交易", end="")
                
                self.simulate_network_delay()
            
            duration = time.time() - start_time
            
            # 计算结果
            self.results[scenario.name] = {
                "duration": duration,
                "avg_tps": sum(metrics["tps_samples"]) / len(metrics["tps_samples"]) if metrics["tps_samples"] else 0,
                "avg_latency": sum(metrics["latencies"]) / len(metrics["latencies"]) if metrics["latencies"] else 0,
                "avg_cross_shard_latency": sum(metrics["cross_shard_latencies"]) / len(metrics["cross_shard_latencies"]) if metrics["cross_shard_latencies"] else 0,
                "avg_cpu_usage": sum(metrics["cpu_samples"]) / len(metrics["cpu_samples"]) if metrics["cpu_samples"] else 0,
                "avg_memory_usage": sum(metrics["memory_samples"]) / len(metrics["memory_samples"]) if metrics["memory_samples"] else 0,
                "total_tx": processed_tx,
                "cross_shard_tx": len(metrics["cross_shard_latencies"])
            }
            
            print(f"\n场景 {scenario.name} 完成")
            print(f"总耗时: {duration:.2f} 秒")
            print(f"平均TPS: {self.results[scenario.name]['avg_tps']:.2f}")
            
        except Exception as e:
            print(f"\n测试出错: {str(e)}")
            print(f"错误类型: {type(e)}")
            import traceback
            traceback.print_exc()

    def run_all_tests(self):
        """运行所有测试场景"""
        print("开始分片性能测试套件...")
        
        for i, scenario in enumerate(self.scenarios, 1):
            print(f"\n[{i}/{len(self.scenarios)}] ", end="")
            self.run_scenario(scenario)
            
            if i < len(self.scenarios):
                print("\n系统冷却中...")
                for j in range(5, 0, -1):
                    print(f"\r休息 {j} 秒", end="")
                    time.sleep(1)
                print("\r" + " " * 20 + "\r", end="")
        
        self.print_summary()

    def print_summary(self):
        """打印测试总结"""
        print("\n=== 分片性能测试总结 ===")
        
        headers = ["场景", "TPS", "普通延迟(ms)", "跨分片延迟(ms)", "跨分片比例", "CPU(%)", "内存(MB)"]
        rows = []
        
        for name, result in self.results.items():
            cross_shard_ratio = result["cross_shard_tx"] / result["total_tx"]
            rows.append([
                name,
                f"{result['avg_tps']:.2f}",
                f"{result['avg_latency']*1000:.2f}",
                f"{result['avg_cross_shard_latency']*1000:.2f}",
                f"{cross_shard_ratio:.1%}",
                f"{result['avg_cpu_usage']:.1f}",
                f"{result['avg_memory_usage']:.1f}"
            ])
        
        # 打印表格
        self._print_table(headers, rows)
        
        # 输出分析建议
        self._generate_recommendations()

    def _print_table(self, headers: List[str], rows: List[List[str]]):
        """打印格式化表格，确保对齐"""
        # 计算每列的最大宽度（包括中文字符）
        def get_string_width(s: str) -> int:
            width = 0
            for char in str(s):
                width += 2 if ord(char) > 127 else 1
            return width
        
        # 计算每列所需的最小宽度
        widths = []
        for i in range(len(headers)):
            col_width = get_string_width(headers[i])
            for row in rows:
                col_width = max(col_width, get_string_width(row[i]))
            widths.append(col_width + 2)  # 添加padding
        
        # 创建分隔线
        separator = "+" + "+".join("-" * w for w in widths) + "+"
        
        # 打印表头
        print(separator)
        header_cells = []
        for h, w in zip(headers, widths):
            space = w - get_string_width(h)
            header_cells.append(f"{h}{' ' * space}")
        print("|" + "|".join(header_cells) + "|")
        print(separator)
        
        # 打印数据行
        for row in rows:
            cells = []
            for cell, w in zip(row, widths):
                space = w - get_string_width(cell)
                cells.append(f"{cell}{' ' * space}")
            print("|" + "|".join(cells) + "|")
        print(separator)

    def _generate_recommendations(self):
        """生成优化建议"""
        print("\n性能优化建议:")
        
        # 分析跨分片交易的影响
        base_latency = self.results["基准测试"]["avg_latency"]
        high_cross_latency = self.results["高跨分片"]["avg_latency"]
        if high_cross_latency > base_latency * 2:
            print("1. 跨分片交易延迟显著，建议优化跨分片通信机制")
            
        # 分析分片扩展性
        base_tps = self.results["基准测试"]["avg_tps"]
        large_shard_tps = self.results["大规模分片"]["avg_tps"]
        if large_shard_tps < base_tps * 1.5:
            print("2. 分片扩展效果不理想，建议优化分片间的负载均衡")
        
        # 分析高TPS场景
        high_tps_latency = self.results["高TPS测试"]["avg_latency"]
        if high_tps_latency > base_latency * 3:
            print("3. 高TPS场景下延迟增长显著，建议优化单片处理能力")

def main():
    tester = ShardPerformanceTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 