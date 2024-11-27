import asyncio
import time
from shard_adjustment import DynamicShardManager
from time_sharding import TimeShardingManager
from transaction_router import TransactionRouter, Transaction
from cross_shard import CrossShardManager
from state_sync import StateSyncManager
from network import P2PNetwork

class ShardAdjustmentTest:
    def __init__(self):
        self.network = P2PNetwork()
        self.time_sharding = TimeShardingManager(
            slot_duration=2,
            shard_count=4,
            validators_per_shard=6  # 增加初始验证者数量以便测试分裂
        )
        self.cross_shard = CrossShardManager(
            time_sharding=self.time_sharding,
            network=self.network
        )
        self.tx_router = TransactionRouter(
            time_sharding=self.time_sharding,
            cross_shard=self.cross_shard
        )
        self.state_sync = StateSyncManager(
            time_sharding=self.time_sharding,
            network=self.network
        )
        self.dynamic_shard = DynamicShardManager(
            time_sharding=self.time_sharding,
            tx_router=self.tx_router,
            state_sync=self.state_sync,
            adjustment_threshold=0.3  # 降低阈值
        )
        
    async def test_metrics_collection(self):
        """测试指标收集"""
        print("\n=== 测试性能指标收集 ===")
        
        # 初始化分片系统
        validators = [f"validator_{i}" for i in range(24)]  # 4个分片，每个6个验证者
        self.time_sharding.initialize_shards(validators)
        
        # 创建测试交易
        for shard_id in range(self.time_sharding.shard_count):
            tx_count = (shard_id + 1) * 200  # 增加交易数量
            for i in range(tx_count):
                tx_id = f"tx_{time.time()}_{shard_id}_{i}"
                self.tx_router.route_transaction(Transaction(
                    tx_id=tx_id,
                    from_shard=shard_id,
                    to_shard=shard_id,
                    data={"amount": 100}
                ))
                
        # 收集并显示指标
        metrics = self.dynamic_shard.collect_metrics()
        for shard_id, metric in metrics.items():
            print(f"\n分片 {shard_id} 指标:")
            print(f"交易数量: {metric.tx_count}")
            print(f"验证者数量: {metric.validator_count}")
            print(f"平均延迟: {metric.tx_latency:.2f}秒")
            print(f"负载因子: {metric.load_factor:.2f}")
            
    async def test_shard_adjustment(self):
        """测试分片调整"""
        print("\n=== 测试分片调整 ===")
        
        # 触发分片调整
        adjusted = self.dynamic_shard.adjust_shards()
        
        if adjusted:
            print("\n分片已调整:")
            for shard_id, shard in self.time_sharding.shards.items():
                print(f"\n分片 {shard_id}:")
                print(f"验证者数量: {len(shard.validators)}")
                print(f"验证者列表: {list(shard.validators)}")
        else:
            print("\n无需调整分片")
            
    async def run_all_tests(self):
        """运行所有测试"""
        await self.test_metrics_collection()
        await self.test_shard_adjustment()

async def main():
    tester = ShardAdjustmentTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 