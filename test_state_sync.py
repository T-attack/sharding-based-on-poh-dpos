import asyncio
from state_sync import StateSyncManager
from time_sharding import TimeShardingManager
from network import P2PNetwork

class StateSyncTest:
    def __init__(self):
        self.network = P2PNetwork()
        self.time_sharding = TimeShardingManager(
            slot_duration=2,
            shard_count=4,
            validators_per_shard=3
        )
        self.state_sync = StateSyncManager(
            time_sharding=self.time_sharding,
            network=self.network
        )
        
    async def test_state_updates(self):
        """测试状态更新"""
        print("\n=== 测试状态更新 ===")
        
        # 初始化分片
        validators = [f"validator_{i}" for i in range(12)]
        self.time_sharding.initialize_shards(validators)
        print("分片系统初始化完成")
        
        # 创建测试状态更新
        test_updates = [
            (0, {"balance": 1000}),
            (1, {"balance": 2000}),
            (2, {"balance": 3000}),
        ]
        
        # 应用状态更新
        update_ids = []
        for shard_id, data in test_updates:
            update_id = self.state_sync.update_state(shard_id, data)
            update_ids.append(update_id)
            print(f"\n更新分片 {shard_id} 状态:")
            print(f"数据: {data}")
            print(f"更新ID: {update_id}")
            
        # 等待状态同步
        await asyncio.sleep(self.time_sharding.slot_duration)
        
        # 同步并验证状态
        print("\n同步分片状态:")
        for shard_id in range(self.time_sharding.shard_count):
            success = self.state_sync.sync_state(shard_id)
            state = self.state_sync.get_shard_state(shard_id)
            print(f"\n分片 {shard_id}:")
            print(f"同步状态: {'成功' if success else '失败'}")
            print(f"当前状态: {state}")
            
    async def run_all_tests(self):
        """运行所有测试"""
        await self.test_state_updates()

async def main():
    tester = StateSyncTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 