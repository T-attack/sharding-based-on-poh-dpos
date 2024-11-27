from typing import List, Dict, Set, Optional
from dataclasses import dataclass
import random
from time_sharding import TimeShardingManager, Shard, TimeSlot

@dataclass
class ShardAssignment:
    """验证者分片分配"""
    validator: str
    shard_id: int
    stake: float
    performance_score: float = 1.0  # 验证者表现评分

class ShardManager:
    def __init__(self, 
                 time_sharding: TimeShardingManager,
                 min_validators_per_shard: int = 3):
        self.time_sharding = time_sharding
        self.min_validators_per_shard = min_validators_per_shard
        self.assignments: Dict[str, ShardAssignment] = {}
        self.shard_validators: Dict[int, Set[str]] = {}
        self.validator_stakes: Dict[str, float] = {}
        
    def initialize_shards(self, validators: List[str], stakes: Dict[str, float]):
        """初始化分片和验证者分配"""
        self.validator_stakes = stakes
        
        # 按质押量排序验证者
        sorted_validators = sorted(
            validators,
            key=lambda v: stakes.get(v, 0),
            reverse=True
        )
        
        # 初始化分片验证者集合
        for shard_id in range(self.time_sharding.shard_count):
            self.shard_validators[shard_id] = set()
            
        # 分配验证者到分片
        for i, validator in enumerate(sorted_validators):
            shard_id = self._select_shard_for_validator(validator)
            self._assign_validator(validator, shard_id, stakes[validator])
            
    def _select_shard_for_validator(self, validator: str) -> int:
        """为验证者选择最合适的分片"""
        # 找到验证者数量最少的分片
        shard_loads = [(len(validators), shard_id) 
                      for shard_id, validators in self.shard_validators.items()]
        min_load = min(shard_loads)
        return min_load[1]
        
    def _assign_validator(self, validator: str, shard_id: int, stake: float):
        """将验证者分配到指定分片"""
        assignment = ShardAssignment(
            validator=validator,
            shard_id=shard_id,
            stake=stake
        )
        self.assignments[validator] = assignment
        self.shard_validators[shard_id].add(validator)
        
    def get_shard_validators(self, shard_id: int) -> Set[str]:
        """获取指定分片的所有验证者"""
        return self.shard_validators.get(shard_id, set())
        
    def get_validator_shard(self, validator: str) -> Optional[int]:
        """获取验证者所在的分片ID"""
        assignment = self.assignments.get(validator)
        return assignment.shard_id if assignment else None
        
    def update_validator_performance(self, validator: str, score: float):
        """更新验证者的性能评分"""
        if validator in self.assignments:
            self.assignments[validator].performance_score = score
            
    def rebalance_shards(self):
        """重新平衡分片负载"""
        # 计算每个分片的总质押量和性能
        shard_metrics = {}
        for shard_id in range(self.time_sharding.shard_count):
            validators = self.shard_validators[shard_id]
            total_stake = sum(self.validator_stakes.get(v, 0) for v in validators)
            avg_performance = sum(self.assignments[v].performance_score 
                                for v in validators) / len(validators) if validators else 0
            shard_metrics[shard_id] = (total_stake, avg_performance)
            
        # 识别负载不均衡的分片
        avg_stake = sum(m[0] for m in shard_metrics.values()) / len(shard_metrics)
        for shard_id, (stake, performance) in shard_metrics.items():
            if stake < avg_stake * 0.8:  # 如果分片质押量显著低于平均值
                self._rebalance_shard(shard_id, avg_stake)
                
    def _rebalance_shard(self, target_shard_id: int, target_stake: float):
        """重新平衡特定分片的负载"""
        current_stake = sum(self.validator_stakes.get(v, 0) 
                          for v in self.shard_validators[target_shard_id])
        
        while current_stake < target_stake:
            # 从其他分片找到合适的验证者转移
            donor_validator = self._find_donor_validator(target_shard_id)
            if not donor_validator:
                break
                
            # 转移验证者到目标分片
            old_shard = self.assignments[donor_validator].shard_id
            self.shard_validators[old_shard].remove(donor_validator)
            self.shard_validators[target_shard_id].add(donor_validator)
            self.assignments[donor_validator].shard_id = target_shard_id
            
            current_stake += self.validator_stakes[donor_validator]
