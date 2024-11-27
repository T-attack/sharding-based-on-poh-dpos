import asyncio
from transaction_router import TransactionRouter, Transaction
from time_sharding import TimeShardingManager
from cross_shard import CrossShardManager
from network import P2PNetwork

class TransactionRouterTest:
    def __init__(self):
        self.network = P2PNetwork()
        self.time_sharding = TimeShardingManager(
            slot_duration=2,
            shard_count=4,
            validators_per_shard=3
        )
        self.cross_shard = CrossShardManager(
            time_sharding=self.time_sharding,
            network=self.network
        )
        self.router = TransactionRouter(
            time_sharding=self.time_sharding,
            cross_shard=self.cross_shard
        )
        
    async def test_transaction_routing(self):
        """测试交易路由"""
        print("\n=== 测试交易路由 ===")
        
        # 初始化分片系统
        validators = [f"validator_{i}" for i in range(12)]
        self.time_sharding.initialize_shards(validators)
        print("分片系统初始化完成")
        
        # 创建测试交易
        test_transactions = [
            # 分片内交易
            Transaction("tx1", 0, 0, {"amount": 100}),
            # 跨分片交易
            Transaction("tx2", 1, 2, {"amount": 200}),
            Transaction("tx3", 2, 3, {"amount": 300}),
        ]
        
        # 路由交易
        for tx in test_transactions:
            success = self.router.route_transaction(tx)
            print(f"\n路由交易 {tx.tx_id}:")
            print(f"从分片 {tx.from_shard} 到分片 {tx.to_shard}")
            print(f"状态: {'成功' if success else '失败'}")
        
        # 等待跨分片消息处理
        await asyncio.sleep(self.time_sharding.slot_duration)
        
        # 处理每个分片的交易
        for shard_id in range(self.time_sharding.shard_count):
            print(f"\n处理分片 {shard_id} 的交易:")
            # 先处理跨分片消息
            self.cross_shard.process_messages(shard_id)
            
            processed = self.router.process_shard_transactions(shard_id)
            print(f"处理完成的交易数量: {len(processed)}")
            for tx in processed:
                print(f"- 交易 {tx.tx_id}: {tx.status}")
                
    async def run_all_tests(self):
        """运行所有测试"""
        await self.test_transaction_routing()

async def main():
    tester = TransactionRouterTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 