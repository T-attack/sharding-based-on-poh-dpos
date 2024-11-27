import asyncio
from time_sharding import TimeShardingManager
from shard_manager import ShardManager
from typing import Dict, List
import random

class ShardingTester:
    def __init__(self):
        self.time_sharding = TimeShardingManager(
            slot_duration=10,
            shard_count=4,
            validators_per_shard=5
        )
        self.shard_manager = ShardManager(
            time_sharding=self.time_sharding,
            min_validators_per_shard=3
        )
        
    def generate_test_validators(self, count: int) -> tuple[List[str], Dict[str, float]]:
        """生成测试验证者和质押数据"""
        validators = [f"validator_{i}" for i in range(count)]
        stakes = {v: random.uniform(1000, 10000) for v in validators}
        return validators, stakes
        
    async def test_shard_initialization(self):
        """测试分片初始化"""
        print("\n=== 测试分片初始化 ===")
        validators, stakes = self.generate_test_validators(20)
        
        print(f"初始验证者数量: {len(validators)}")
        print("质押分布:")
        for v, s in sorted(stakes.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"{v}: {s:.2f}")
            
        self.shard_manager.initialize_shards(validators, stakes)
        
        # 验证分片分配
        print("\n分片分配结果:")
        for shard_id in range(self.time_sharding.shard_count):
            validators = self.shard_manager.get_shard_validators(shard_id)
            total_stake = sum(stakes[v] for v in validators)
            print(f"\n分片 {shard_id}:")
            print(f"验证者数量: {len(validators)}")
            print(f"总质押量: {total_stake:.2f}")
            print(f"验证者列表: {', '.join(sorted(validators))}")
            
    async def test_validator_reassignment(self):
        """测试验证者重分配"""
        print("\n=== 测试验证者重分配 ===")
        
        # 更新一些验证者的性能分数
        for validator in list(self.shard_manager.assignments.keys())[:5]:
            new_score = random.uniform(0.5, 1.0)
            self.shard_manager.update_validator_performance(validator, new_score)
            print(f"更新 {validator} 的性能分数为: {new_score:.2f}")
            
        # 执行分片重平衡
        print("\n执行分片重平衡...")
        self.shard_manager.rebalance_shards()
        
        # 显示重平衡结果
        print("\n重平衡后的分片分布:")
        for shard_id in range(self.time_sharding.shard_count):
            validators = self.shard_manager.get_shard_validators(shard_id)
            print(f"\n分片 {shard_id}:")
            print(f"验证者数量: {len(validators)}")
            print(f"验证者列表: {', '.join(sorted(validators))}")
            
    async def test_time_slot_assignment(self):
        """测试时间槽分配"""
        print("\n=== 测试时间槽分配 ===")
        
        # 获取当前时间槽
        current_slot = self.time_sharding.get_current_time_slot()
        print(f"\n当前时间槽信息:")
        print(f"槽ID: {current_slot.slot_id}")
        print(f"开始时间: {current_slot.start_time}")
        print(f"结束时间: {current_slot.end_time}")
        print(f"验证者组大小: {len(current_slot.validator_group)}")
        print(f"验证者组: {', '.join(sorted(current_slot.validator_group))}")
        
    async def run_all_tests(self):
        """运行所有测试"""
        # 先初始化分片
        await self.test_shard_initialization()
        
        # 初始化 TimeShardingManager 的分片
        validators, _ = self.generate_test_validators(20)
        self.time_sharding.initialize_shards(validators)
        
        # 再运行其他测试
        await self.test_validator_reassignment()
        await self.test_time_slot_assignment()

async def main():
    tester = ShardingTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 