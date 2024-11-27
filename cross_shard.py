from dataclasses import dataclass
from typing import List, Dict, Set, Optional
import time
from network import NetworkMessage, P2PNetwork
from time_sharding import TimeShardingManager, Shard
from transaction_router import Transaction

@dataclass
class CrossShardMessage:
    """跨分片消息"""
    message_id: str
    from_shard: int
    to_shard: int
    data: dict
    timestamp: float
    status: str = "pending"  # pending, delivered, confirmed
    
class CrossShardManager:
    def __init__(self, 
                 time_sharding: TimeShardingManager,
                 network: P2PNetwork):
        self.time_sharding = time_sharding
        self.network = network
        self.message_queue: Dict[int, List[CrossShardMessage]] = {}
        self.pending_messages: Dict[str, CrossShardMessage] = {}
        self.confirmed_messages: Set[str] = set()
        self.cross_shard_messages = {
            shard_id: [] for shard_id in range(time_sharding.shard_count)
        }
        
    def send_cross_shard_message(self, from_shard: int, to_shard: int, data: dict) -> str:
        """发送跨分片消息"""
        message = CrossShardMessage(
            message_id=f"msg_{time.time()}_{from_shard}_{to_shard}",
            from_shard=from_shard,
            to_shard=to_shard,
            data=data,
            timestamp=time.time()
        )
        
        # 将消息添加到队列
        if to_shard not in self.message_queue:
            self.message_queue[to_shard] = []
        self.message_queue[to_shard].append(message)
        self.pending_messages[message.message_id] = message
        
        # 广播消息到网络
        self.network.broadcast(NetworkMessage(
            "CROSS_SHARD_MSG",
            {"message": message}
        ))
        
        return message.message_id
        
    def process_messages(self, current_shard: int):
        """处理当前分片的消息队列"""
        if current_shard not in self.message_queue:
            return
            
        messages = self.message_queue[current_shard]
        processed_messages = []
        
        for message in messages:
            if self._process_message(message):
                processed_messages.append(message)
                # 直接确认消息
                self.confirm_message(message.message_id)
        
        # 移除已处理的消息
        for message in processed_messages:
            messages.remove(message)
        
    def _process_message(self, message: CrossShardMessage) -> bool:
        """处理单个跨分片消息"""
        # 验证目标分片是否准备好接收消息
        if not self._verify_shard_ready(message.to_shard):
            return False
            
        # 更新消息状态
        message.status = "delivered"
        
        # 发送确认消息
        self.network.broadcast(NetworkMessage(
            "CROSS_SHARD_CONFIRM",
            {
                "message_id": message.message_id,
                "from_shard": message.from_shard,
                "to_shard": message.to_shard
            }
        ))
        
        return True
        
    def _verify_shard_ready(self, shard_id: int) -> bool:
        """验证分片是否准备好接收消息"""
        try:
            # 检查分片ID是否有效
            if shard_id >= self.time_sharding.shard_count:
                return False
            
            # 检查分片是否已初始化
            if shard_id not in self.time_sharding.shards:
                return False
            
            # 获取当前时间槽
            current_slot = self.time_sharding.get_current_time_slot()
            shard = self.time_sharding.shards[shard_id]
            
            # 检查分片是否有��证者
            if not shard.validators:
                return False
            
            return True
        
        except Exception as e:
            print(f"验证分片就绪状态时出错: {str(e)}")
            # 在开发环境中，我们暂时允许继续处理
            return True
        
    def confirm_message(self, message_id: str):
        """确认消息已被处理"""
        if message_id in self.pending_messages:
            message = self.pending_messages[message_id]
            message.status = "confirmed"
            self.confirmed_messages.add(message_id)
            del self.pending_messages[message_id] 
        
    def handle_cross_shard_transaction(self, tx: Transaction):
        """处理跨分片交易"""
        # 创建跨分片消息
        message = CrossShardMessage(
            message_id=f"tx_{time.time()}_{tx.from_shard}_{tx.to_shard}",
            from_shard=tx.from_shard,
            to_shard=tx.to_shard,
            data=tx.data,
            timestamp=time.time()
        )
        
        # 将消息添加到目标分片的消息队列
        self.cross_shard_messages[tx.to_shard].append(message)
        return True 