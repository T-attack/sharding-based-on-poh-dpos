from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import time
from time_sharding import TimeShardingManager, Shard
from transaction_router import TransactionRouter
from state_sync import StateSyncManager

@dataclass
class ShardMetrics:
    """分片性能指标"""
    tx_count: int = 0          # 交易数量
    tx_latency: float = 0      # 平均交易延迟
    validator_count: int = 0    # 验证者数量
    load_factor: float = 0     # 负载因子
    
class DynamicShardManager:
    def __init__(self,
                 time_sharding: TimeShardingManager,
                 tx_router: TransactionRouter,
                 state_sync: StateSyncManager,
                 adjustment_threshold: float = 0.8,  # 触发调整的负载阈值
                 min_shard_size: int = 3):          # 最小分片验证者数量
        self.time_sharding = time_sharding
        self.tx_router = tx_router
        self.state_sync = state_sync
        self.adjustment_threshold = adjustment_threshold
        self.min_shard_size = min_shard_size
        self.shard_metrics: Dict[int, ShardMetrics] = {}
        
    def collect_metrics(self) -> Dict[int, ShardMetrics]:
        """收集分片性能指标"""
        metrics = {}
        for shard_id in range(self.time_sharding.shard_count):
            if shard_id in self.time_sharding.shards:
                shard = self.time_sharding.shards[shard_id]
                tx_pool = self.tx_router.tx_pools.get(shard_id, [])
                
                metrics[shard_id] = ShardMetrics(
                    tx_count=len(tx_pool),
                    validator_count=len(shard.validators),
                    tx_latency=self._calculate_tx_latency(tx_pool),
                    load_factor=self._calculate_load_factor(shard, tx_pool)
                )
                
        self.shard_metrics = metrics
        return metrics
        
    def _calculate_tx_latency(self, tx_pool: List) -> float:
        """计算平均交易延迟"""
        if not tx_pool:
            return 0.0
            
        current_time = time.time()
        latencies = []
        for tx in tx_pool:
            # 假设交易的tx_id包含时间戳
            tx_time = float(tx.tx_id.split('_')[1])
            latencies.append(current_time - tx_time)
            
        return sum(latencies) / len(latencies)
        
    def _calculate_load_factor(self, shard: Shard, tx_pool: List) -> float:
        """计算分片负载因子"""
        validator_capacity = len(shard.validators) * 100  # 假设每个验证者可处理100笔交易
        return len(tx_pool) / validator_capacity if validator_capacity > 0 else 1.0
        
    def adjust_shards(self) -> bool:
        """动态调整分片"""
        try:
            metrics = self.collect_metrics()
            
            # 找出负载过高和过低的分片
            overloaded_shards = []
            underloaded_shards = []
            
            for shard_id, metric in metrics.items():
                if metric.load_factor >= self.adjustment_threshold:
                    overloaded_shards.append(shard_id)
                elif metric.load_factor < self.adjustment_threshold / 2:
                    underloaded_shards.append(shard_id)
                    
            if not overloaded_shards:
                return False
                
            # 对每个过载分片进行处理
            for shard_id in overloaded_shards:
                self._handle_overloaded_shard(shard_id, underloaded_shards)
                
            return True
            
        except Exception as e:
            print(f"调整分片时出错: {e}")
            return False
            
    def _handle_overloaded_shard(self, shard_id: int, underloaded_shards: List[int]):
        """处理过载分片"""
        shard = self.time_sharding.shards[shard_id]
        metrics = self.shard_metrics[shard_id]
        
        # 策略1: 重新分配验证者
        if underloaded_shards:
            target_shard_id = underloaded_shards[0]
            self._redistribute_validators(shard_id, target_shard_id)
            
        # 策略2: 分裂分片
        elif len(shard.validators) >= self.min_shard_size * 2:
            self._split_shard(shard_id)
            
    def _redistribute_validators(self, from_shard: int, to_shard: int):
        """重新分配验证者"""
        source_shard = self.time_sharding.shards[from_shard]
        target_shard = self.time_sharding.shards[to_shard]
        
        # 计算需要转移的验证者数量
        transfer_count = len(source_shard.validators) // 3
        
        if transfer_count < 1:
            return
            
        # 选择要转移的验证者
        validators_to_move = list(source_shard.validators)[:transfer_count]
        
        # 更新分片的验证者集合
        source_shard.validators -= set(validators_to_move)
        target_shard.validators |= set(validators_to_move)
        
        # 同步状态
        self.state_sync.update_state(from_shard, {"validators": list(source_shard.validators)})
        self.state_sync.update_state(to_shard, {"validators": list(target_shard.validators)})
        
    def _split_shard(self, shard_id: int):
        """分裂分片"""
        shard = self.time_sharding.shards[shard_id]
        validators = list(shard.validators)
        mid = len(validators) // 2
        
        # 创建新分片
        new_shard_id = len(self.time_sharding.shards)
        new_shard = Shard(
            shard_id=new_shard_id,
            validators=set(validators[mid:]),
            time_slots=[],
            transactions=[]
        )
        
        # 更新原分片
        shard.validators = set(validators[:mid])
        
        # 添加新分片
        self.time_sharding.shards[new_shard_id] = new_shard
        self.time_sharding.shard_count += 1
        
        # 同步状态
        self.state_sync.update_state(shard_id, {"validators": list(shard.validators)})
        self.state_sync.update_state(new_shard_id, {"validators": list(new_shard.validators)}) 