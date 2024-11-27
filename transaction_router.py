from dataclasses import dataclass
from typing import List, Dict, Optional
import asyncio

@dataclass
class Transaction:
    """交易结构"""
    tx_id: str
    from_shard: int
    to_shard: int
    data: dict

class TransactionRouter:
    def __init__(self, time_sharding, cross_shard_manager):
        self.time_sharding = time_sharding
        self.cross_shard_manager = cross_shard_manager
        # 为每个分片初始化交易池
        self.tx_pools = {
            shard_id: [] for shard_id in range(time_sharding.shard_count)
        }
        self.shard_transactions = {
            shard_id: [] for shard_id in range(time_sharding.shard_count)
        }

    def route_transaction(self, tx: Transaction):
        """同步版本的交易路由"""
        if tx.from_shard == tx.to_shard:
            self.tx_pools[tx.from_shard].append(tx)
        else:
            self.cross_shard_manager.handle_cross_shard_transaction(tx)
        return True
        
    def process_shard_transactions(self, shard_id: int) -> List[Transaction]:
        """同步处理分片交易"""
        txs = self.tx_pools.get(shard_id, [])
        self.tx_pools[shard_id] = []
        return txs