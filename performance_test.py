import asyncio
import signal
import sys
from typing import List
import random
import time
from dpos import PerformanceMonitor, ConsensusSystem, DPOS
from poh import ProofOfHistory

class PerformanceTester:
    def __init__(self, 
                 transaction_count: int = 10000,
                 batch_size: int = 100,
                 validator_count: int = 21):
        self.transaction_count = transaction_count
        self.batch_size = batch_size
        self.validator_count = validator_count
        self.is_running = True
        self.consensus = None
        
    def stop(self):
        """停止测试"""
        print("\n正在停止测试...")
        self.is_running = False
                
    async def generate_transactions(self) -> List[str]:
        """生成测试交易"""
        return [f"tx_{i}_{random.randint(0, 1000000)}" 
                for i in range(self.batch_size)]
                
    async def run_test(self):
        """运行性能测试"""
        # 初始化系统
        poh = ProofOfHistory(difficulty=3)
        dpos = DPOS(max_validators=self.validator_count)
        self.consensus = ConsensusSystem(poh, dpos)
        
        # 注册验证者
        for i in range(self.validator_count):
            validator = f"validator_{i}"
            dpos.stake(validator, 1000)
            dpos.register_validator(validator)
            
        dpos.update_active_validators()
        
        # 开始性能监控
        start_time = time.time()
        processed_tx = 0
        
        try:
            while processed_tx < self.transaction_count and self.is_running:
                transactions = await self.generate_transactions()
                validator = dpos.get_next_block_validator()
                block_start = time.time()
                block = self.consensus.create_block(validator, transactions)
                
                latency = time.time() - block_start
                self.consensus.performance_monitor.record_transaction_latency(latency)
                self.consensus.performance_monitor.collect_system_metrics()
                
                processed_tx += len(transactions)
                print(f"\r进度: {processed_tx}/{self.transaction_count} 交易", end="")
                
                await asyncio.sleep(dpos.block_interval)
                
        except KeyboardInterrupt:
            print("\n检测到用户中断...")
        finally:
            duration = time.time() - start_time
            print(f"\n测试运行时间: {duration:.2f} 秒")
            report = self.consensus.performance_monitor.generate_report()
            self._print_report(report)

    def _print_report(self, report: dict):
        print("\n=== 性能测试报告 ===")
        print(f"总交易数: {report['total_transactions']}")
        print(f"TPS: {report['tps']:.2f}")
        print(f"平均延迟: {report['average_latency']*1000:.2f}ms")
        print(f"平均CPU使用率: {report['avg_cpu_usage']:.2f}%")
        print(f"平均内存使用: {report['avg_memory_usage']:.2f}MB")
        print(f"总区块数: {report['block_count']}")

    def get_metrics(self) -> dict:
        """获取性能指标"""
        if not self.consensus:
            return {}
        return self.consensus.performance_monitor.generate_report()

async def main():
    tester = PerformanceTester(
        transaction_count=10000,
        batch_size=100,
        validator_count=21
    )
    
    # 设置信号处理
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda _sig, _frame: tester.stop())
    
    await tester.run_test()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已终止")
        sys.exit(0) 