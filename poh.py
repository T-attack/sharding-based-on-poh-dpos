import hashlib
import time
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class HistoryNode:
    """历史节点数据结构"""
    sequence: int          # 序列号
    hash: str             # 当前哈希值
    data: Optional[str]   # 可选的交易数据
    timestamp: float      # 时间戳
    counter: int          # 计数器

class ProofOfHistory:
    def __init__(self, difficulty: int = 8):
        """
        初始化 POH
        :param difficulty: 哈希计算的难度（每次计算的循环次数）
        """
        self.difficulty = difficulty
        self.history: List[HistoryNode] = []
        # 创建创世节点
        genesis = HistoryNode(
            sequence=0,
            hash="0" * 64,
            data=None,
            timestamp=time.time(),
            counter=0
        )
        self.history.append(genesis)

    def _hash(self, previous_hash: str, data: Optional[str] = None) -> str:
        """
        计算哈希值
        """
        hasher = hashlib.sha256()
        hasher.update(previous_hash.encode())
        if data:
            hasher.update(data.encode())
        return hasher.hexdigest()

    def tick(self, data: Optional[str] = None) -> HistoryNode:
        """
        生成下一个历史节点
        :param data: 可选的交易数据
        """
        previous_node = self.history[-1]
        current_hash = previous_node.hash
        
        # 执行指定次数的哈希计算
        for _ in range(self.difficulty):
            current_hash = self._hash(current_hash)
        
        # 如果有数据，将数据加入最后一次哈希计算
        if data:
            current_hash = self._hash(current_hash, data)
        
        # 创建新节点
        new_node = HistoryNode(
            sequence=previous_node.sequence + 1,
            hash=current_hash,
            data=data,
            timestamp=time.time(),
            counter=previous_node.counter + self.difficulty + (1 if data else 0)
        )
        
        self.history.append(new_node)
        return new_node

    def verify(self, start_index: int, end_index: int) -> bool:
        """
        验证历史记录的完整性
        """
        if start_index < 0 or end_index >= len(self.history):
            return False
            
        for i in range(start_index, end_index):
            current_node = self.history[i]
            next_node = self.history[i + 1]
            
            # 验证哈希链
            current_hash = current_node.hash
            for _ in range(self.difficulty):
                current_hash = self._hash(current_hash)
                
            if next_node.data:
                current_hash = self._hash(current_hash, next_node.data)
                
            if current_hash != next_node.hash:
                return False
                
        return True

# 使用示例
def demo_poh():
    poh = ProofOfHistory(difficulty=3)
    
    # 生成一些历史记录
    poh.tick()  # 空节点
    poh.tick("Transaction 1")  # 包含交易数据的节点
    poh.tick()
    poh.tick("Transaction 2")
    
    # 打印历史记录
    for node in poh.history:
        print(f"Sequence: {node.sequence}")
        print(f"Hash: {node.hash}")
        print(f"Data: {node.data}")
        print(f"Counter: {node.counter}")
        print("---")
    
    # 验证历史记录
    is_valid = poh.verify(0, 3)
    print(f"History verification: {is_valid}")

if __name__ == "__main__":
    demo_poh()