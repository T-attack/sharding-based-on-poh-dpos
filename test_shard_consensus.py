import asyncio
import time
from poh import ProofOfHistory
from dpos import DPOS, ConsensusSystem
from time_sharding import TimeShardingManager
from cross_shard import CrossShardManager
from network import P2PNetwork, NetworkMessage

class ShardConsensusTest:
    def __init__(self):
        self.network = P2PNetwork()
        self.time_sharding = TimeShardingManager(
            slot_duration=2,  # 缩短时间槽便于测试
            shard_count=4,
            validators_per_shard=3
        )
        self.poh = ProofOfHistory(difficulty=3)
        self.dpos = DPOS(max_validators=12)  # 4个分片，每个3个验证者
        
    async def setup_test_environment(self):
        """设置测试环境"""
        print("\n=== 初始化测试环境 ===")
        
        # 生成测试验证者
        validators = [f"validator_{i}" for i in range(12)]
        
        # 为每个验证者质押和注册
        for validator in validators:
            self.dpos.stake(validator, 1000)
            self.dpos.register_validator(validator)
            print(f"注册验证者: {validator}")
            
        # 初始化分片
        self.time_sharding.initialize_shards(validators)
        print("\n分片初始化完成")
        
        return validators
        
    async def test_shard_block_creation(self, validators):
        """测试分片区块创建"""
        print("\n=== 测试分片区块创建 ===")
        
        for shard_id in range(self.time_sharding.shard_count):
            print(f"\n处理分片 {shard_id}:")
            
            # 获取分片验证者
            shard = self.time_sharding.shards[shard_id]
            shard_validators = list(shard.validators)
            
            # 创建分片交易
            transactions = [
                f"tx_shard_{shard_id}_{i}" 
                for i in range(3)
            ]
            
            # 选择验证者并创建区块
            validator = shard_validators[0]
            consensus = ConsensusSystem(
                poh=self.poh, 
                dpos=self.dpos,
                shard_id=shard_id  # 添加分片ID
            )
            block = consensus.create_block(validator, transactions)
            
            print(f"验证者 {validator} 创建区块:")
            print(f"- 高度: {block.height}")
            print(f"- 交易数: {len(block.transactions)}")
            print(f"- POH哈希: {block.poh_hash[:16]}...")
            
    async def test_cross_shard_consensus(self):
        """测试跨分片共识"""
        print("\n=== 测试跨分片共识 ===")
        
        cross_shard = CrossShardManager(
            time_sharding=self.time_sharding,
            network=self.network
        )
        
        # 创建跨分片交易
        test_messages = [
            (0, 2, {"type": "cross_shard_tx", "amount": 100}),
            (1, 3, {"type": "cross_shard_tx", "amount": 200}),
        ]
        
        # 发送和处理跨分片消息
        for from_shard, to_shard, data in test_messages:
            msg_id = cross_shard.send_cross_shard_message(
                from_shard=from_shard,
                to_shard=to_shard,
                data=data
            )
            print(f"\n发送跨分片交易: {from_shard} -> {to_shard}")
            print(f"消息ID: {msg_id}")
            
            # 处理目标分片的消息
            cross_shard.process_messages(to_shard)
            
            # 检查消息状态
            if msg_id in cross_shard.confirmed_messages:
                print("交易已确认")
            elif msg_id in cross_shard.pending_messages:
                print("交易待处理")
            else:
                print("交易未找到")
                
    async def run_all_tests(self):
        """运行所有测试"""
        validators = await self.setup_test_environment()
        await self.test_shard_block_creation(validators)
        await self.test_cross_shard_consensus()
        
async def main():
    tester = ShardConsensusTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 