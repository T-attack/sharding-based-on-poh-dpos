from dataclasses import dataclass
from typing import List, Optional
import hashlib
import time

@dataclass
class Block:
    """区块结构"""
    height: int              # 区块高度
    timestamp: float         # 时间戳
    previous_hash: str       # 前一个区块的哈希
    transactions: List[str]  # 交易列表
    validator: str           # 出块验证者
    signature: str           # 验证者签名
    poh_hash: str           # POH哈希值

    @property
    def hash(self) -> str:
        """计算区块哈希"""
        block_data = f"{self.height}{self.timestamp}{self.previous_hash}{self.transactions}{self.validator}{self.poh_hash}"
        return hashlib.sha256(block_data.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.create_genesis_block()

    def create_genesis_block(self):
        """创建创世区块"""
        genesis_block = Block(
            height=0,
            timestamp=time.time(),
            previous_hash="0" * 64,
            transactions=[],
            validator="genesis",
            signature="",
            poh_hash="0" * 64
        )
        self.chain.append(genesis_block)

    def add_block(self, block: Block) -> bool:
        """添加新区块"""
        if self.is_valid_block(block):
            self.chain.append(block)
            return True
        return False

    def is_valid_block(self, block: Block) -> bool:
        """验证区块有效性"""
        if not self.chain:
            return block.height == 0
        
        previous_block = self.chain[-1]
        return (block.height == previous_block.height + 1 and
                block.previous_hash == previous_block.hash)

    def get_latest_block(self) -> Optional[Block]:
        """获取最新区块"""
        return self.chain[-1] if self.chain else None 