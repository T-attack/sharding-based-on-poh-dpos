import asyncio
import time
from time_sharding import TimeShardingManager
from cross_shard import CrossShardManager
from network import P2PNetwork, Node
from typing import Dict, List

class CrossShardTester:
    def __init__(self):
        self.network = P2PNetwork()
        self.time_sharding = TimeShardingManager(
            slot_duration=2,  # 缩短时间槽便于测试
            shard_count=4,
            validators_per_shard=3
        )
        self.cross_shard = CrossShardManager(
            time_sharding=self.time_sharding,
            network=self.network
        )
        
    def setup_network(self):
        """设置测试网络"""
        # 为每个分片创建节点
        for shard_id in range(self.time_sharding.shard_count):
            for i in range(3):  # 每个分片3个节点
                node_id = f"node_{shard_id}_{i}"
                self.network.peers[node_id] = Node(node_id)
                
    async def test_cross_shard_messaging(self):
        """测试跨分片消息传输"""
        print("\n=== 测试跨分片消息传输 ===")
        
        # 初始化分片
        validators = [f"validator_{i}" for i in range(12)]  # 4个分片，每个3个验证者
        self.time_sharding.initialize_shards(validators)
        
        # 发送测试消息
        test_messages = [
            (0, 2, {"type": "transfer", "amount": 100}),
            (1, 3, {"type": "transfer", "amount": 200}),
            (2, 0, {"type": "transfer", "amount": 300}),
        ]
        
        message_ids = []
        print("\n发送跨分片消息:")
        for from_shard, to_shard, data in test_messages:
            msg_id = self.cross_shard.send_cross_shard_message(
                from_shard=from_shard,
                to_shard=to_shard,
                data=data
            )
            message_ids.append(msg_id)
            print(f"消息已发送: {from_shard} -> {to_shard}, 数据: {data}")
            
        # 等待消息处理
        print("\n处理消息队列:")
        for current_shard in range(self.time_sharding.shard_count):
            print(f"\n处理分片 {current_shard} 的消息:")
            self.cross_shard.process_messages(current_shard)
            
            # 显示该分片的消息状态
            if current_shard in self.cross_shard.message_queue:
                messages = self.cross_shard.message_queue[current_shard]
                print(f"待处理消息数量: {len(messages)}")
                for msg in messages:
                    print(f"- 消息ID: {msg.message_id}, 状态: {msg.status}")
                    
        # 验证消息确认
        print("\n消息确认状态:")
        for msg_id in message_ids:
            if msg_id in self.cross_shard.confirmed_messages:
                print(f"消息 {msg_id} 已确认")
            elif msg_id in self.cross_shard.pending_messages:
                print(f"消息 {msg_id} 待处理")
            else:
                print(f"消息 {msg_id} 未找到")
                
    async def test_message_timing(self):
        """测试消息时序"""
        print("\n=== 测试消息时序 ===")
        
        # 发送消息并记录时间
        start_time = time.time()
        msg_id = self.cross_shard.send_cross_shard_message(
            from_shard=0,
            to_shard=1,
            data={"type": "timing_test"}
        )
        
        # 等待几个时间槽
        await asyncio.sleep(self.time_sharding.slot_duration * 2)
        
        # 处理消息
        self.cross_shard.process_messages(1)
        
        # 检查消息状态和处理时间
        end_time = time.time()
        if msg_id in self.cross_shard.confirmed_messages:
            print(f"消息处理完成，耗时: {end_time - start_time:.2f}秒")
        else:
            print("消息未在预期时间内完成处理")
            
    async def run_all_tests(self):
        """运行所有测试"""
        self.setup_network()
        await self.test_cross_shard_messaging()
        await self.test_message_timing()

async def main():
    tester = CrossShardTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 