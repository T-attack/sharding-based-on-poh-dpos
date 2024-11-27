from dataclasses import dataclass
from typing import List, Dict, Set
import time

@dataclass
class TimeSlot:
    """时间槽"""
    slot_id: int                # 时间槽ID
    start_time: float           # 开始时间
    end_time: float            # 结束时间
    validator_group: Set[str]   # 该时间槽的验证者组
    
@dataclass
class Shard:
    """分片"""
    shard_id: int              # 分片ID
    validators: Set[str]        # 分片内的验证者
    time_slots: List[TimeSlot]  # 分片的时间槽
    transactions: List[str]     # 待处理交易池
    
class TimeShardingManager:
    def __init__(self, 
                 slot_duration: int = 10,      # 时间槽持续时间（秒）
                 shard_count: int = 4,         # 分片数量
                 validators_per_shard: int = 5  # 每个分片的验证者数量
                ):
        self.slot_duration = slot_duration
        self.shard_count = shard_count
        self.validators_per_shard = validators_per_shard
        self.shards: Dict[int, Shard] = {}
        self.current_slot: TimeSlot = None
        self.global_start_time = time.time()
        
    def initialize_shards(self, all_validators: List[str]):
        """初始化分片"""
        # 将验证者分配到不同分片
        for shard_id in range(self.shard_count):
            start_idx = shard_id * self.validators_per_shard
            end_idx = start_idx + self.validators_per_shard
            shard_validators = set(all_validators[start_idx:end_idx])
            
            self.shards[shard_id] = Shard(
                shard_id=shard_id,
                validators=shard_validators,
                time_slots=[],
                transactions=[]
            )
            
    def get_current_time_slot(self) -> TimeSlot:
        """获取当前时间槽"""
        # 检查是否已初始化
        if not self.shards:
            raise ValueError("分片系统尚未初始化")
        
        current_time = time.time()
        elapsed_time = current_time - self.global_start_time
        slot_id = int(elapsed_time / self.slot_duration)
        
        start_time = self.global_start_time + (slot_id * self.slot_duration)
        end_time = start_time + self.slot_duration
        
        # 确定当前时间槽的验证者组
        shard_id = slot_id % self.shard_count
        if shard_id not in self.shards:
            raise ValueError(f"分片 {shard_id} 未初始化")
        
        validator_group = self.shards[shard_id].validators
        
        return TimeSlot(
            slot_id=slot_id,
            start_time=start_time,
            end_time=end_time,
            validator_group=validator_group
        ) 