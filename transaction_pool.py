from typing import List, Dict, Optional
import time
import asyncio
from dataclasses import dataclass
from collections import OrderedDict
import heapq

@dataclass
class Transaction:
    """交易数据结构"""
    tx_id: str
    data: str
    timestamp: float
    gas_price: float
    size: int

class TransactionPool:
    def __init__(self, 
                 max_size: int = 100000,
                 max_batch_size: int = 5000,
                 min_gas_price: float = 0.1):
        """
        初始化交易池
        :param max_size: 交易池最大容量
        :param max_batch_size: 单个批次最大交易数
        :param min_gas_price: 最低gas价格
        """
        self.max_size = max_size
        self.max_batch_size = max_batch_size
        self.min_gas_price = min_gas_price
        
        self.pending_txs: OrderedDict[str, Transaction] = OrderedDict()
        self.priority_queue: List[tuple[float, str]] = []  # (gas_price, tx_id)
        self._lock = asyncio.Lock()
        self.total_size = 0
        
    async def add_transaction(self, tx: Transaction) -> bool:
        """添加新交易到交易池"""
        async with self._lock:
            # 验证交易
            if not self._validate_transaction(tx):
                return False
                
            # 检查容量
            if len(self.pending_txs) >= self.max_size:
                # 如果新交易gas价格更高,清除最低价格的交易
                if self.priority_queue[0][0] < tx.gas_price:
                    _, removed_tx_id = heapq.heappop(self.priority_queue)
                    removed_tx = self.pending_txs.pop(removed_tx_id)
                    self.total_size -= removed_tx.size
                else:
                    return False
                    
            # 添加交易
            self.pending_txs[tx.tx_id] = tx
            heapq.heappush(self.priority_queue, (tx.gas_price, tx.tx_id))
            self.total_size += tx.size
            return True
            
    def get_batch(self, max_size: Optional[int] = None) -> List[Transaction]:
        """获取待处理的交易批次"""
        batch_size = max_size or self.max_batch_size
        batch: List[Transaction] = []
        current_size = 0
        
        # 优先选择gas价格高的交易
        sorted_txs = sorted(
            self.pending_txs.values(),
            key=lambda x: (-x.gas_price, x.timestamp)
        )
        
        for tx in sorted_txs:
            if len(batch) >= batch_size:
                break
            if current_size + tx.size <= self.max_size:
                batch.append(tx)
                current_size += tx.size
                
        return batch
        
    async def remove_transactions(self, tx_ids: List[str]):
        """移除已处理的交易"""
        async with self._lock:
            for tx_id in tx_ids:
                if tx_id in self.pending_txs:
                    tx = self.pending_txs.pop(tx_id)
                    self.total_size -= tx.size
                    # 更新优先队列
                    self.priority_queue = [
                        (p, tid) for p, tid in self.priority_queue 
                        if tid != tx_id
                    ]
                    heapq.heapify(self.priority_queue)
                    
    def _validate_transaction(self, tx: Transaction) -> bool:
        """验证交易有效性"""
        return (
            tx.gas_price >= self.min_gas_price and
            tx.size > 0 and
            tx.tx_id not in self.pending_txs
        )
        
    @property
    def size(self) -> int:
        """当前交易池大小"""
        return len(self.pending_txs)
        
    @property
    def memory_size(self) -> int:
        """当前占用内存大小(bytes)"""
        return self.total_size
        
    def clear_expired(self, max_age: float = 3600):
        """清理过期交易"""
        current_time = time.time()
        expired_txs = [
            tx_id for tx_id, tx in self.pending_txs.items()
            if current_time - tx.timestamp > max_age
        ]
        return expired_txs 