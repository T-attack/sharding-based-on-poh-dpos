from dataclasses import dataclass
from typing import List, Dict, Set, Optional
import random
import time
import asyncio
from network import P2PNetwork, NetworkMessage
from blockchain import Block, Blockchain
import psutil
import statistics
from collections import defaultdict
from transaction_pool import TransactionPool, Transaction

@dataclass
class Validator:
    """验证者节点"""
    address: str          # 验证者地址
    stake_amount: float   # 质押数量
    votes: float         # 获得的票数
    is_active: bool      # 是否是活跃验证者
    last_block_time: float  # 上次出块时间

@dataclass
class Vote:
    """投票记录"""
    voter: str           # 投票者地址
    candidate: str       # 候选人地址
    amount: float        # 投票数量
    timestamp: float     # 投票时间

@dataclass
class BlockMetrics:
    """区块性能指标"""
    block_height: int
    transactions_count: int
    creation_time: float
    confirmation_time: float
    validator: str
    
@dataclass
class SystemMetrics:
    """系统资源指标"""
    cpu_usage: float
    memory_usage: float
    network_io: Dict[str, int]
    timestamp: float

class DPOS:
    def __init__(self, 
                 max_validators: int = 21,
                 block_interval: float = 0.1):
        """
        初始化 DPOS 系统
        :param max_validators: 最大验证者数量
        :param block_interval: 出块间隔（秒）
        """
        self.max_validators = max_validators
        self.block_interval = block_interval
        
        self.validators: Dict[str, Validator] = {}
        self.votes: List[Vote] = []
        self.stakes: Dict[str, float] = {}
        self.current_epoch = 0
        self.active_validators: Set[str] = set()

    def stake(self, address: str, amount: float) -> bool:
        """
        质押代币
        """
        if amount <= 0:
            return False
        
        self.stakes[address] = self.stakes.get(address, 0) + amount
        return True

    def register_validator(self, address: str) -> bool:
        """
        注册成为验证者
        """
        if address not in self.stakes or self.stakes[address] <= 0:
            return False
            
        if address not in self.validators:
            self.validators[address] = Validator(
                address=address,
                stake_amount=self.stakes[address],
                votes=0,
                is_active=False,
                last_block_time=0
            )
        return True

    def vote(self, voter: str, candidate: str, amount: float) -> bool:
        """
        投票给验证者
        """
        if (voter not in self.stakes or 
            amount > self.stakes[voter] or 
            candidate not in self.validators):
            return False
            
        vote = Vote(
            voter=voter,
            candidate=candidate,
            amount=amount,
            timestamp=time.time()
        )
        
        self.votes.append(vote)
        self.validators[candidate].votes += amount
        return True

    def update_active_validators(self):
        """
        更新活跃验证者列表
        """
        # 按投票数排序验证者
        sorted_validators = sorted(
            self.validators.values(),
            key=lambda x: x.votes,
            reverse=True
        )
        
        # 选择前 max_validators 个作为活跃验证者
        self.active_validators.clear()
        for validator in sorted_validators[:self.max_validators]:
            validator.is_active = True
            self.active_validators.add(validator.address)
            
        # 将其余验证者设置为非活跃
        for validator in sorted_validators[self.max_validators:]:
            validator.is_active = False

    def get_next_block_validator(self) -> str:
        """
        获取下一个出块验证者
        """
        current_time = time.time()
        active_list = sorted(list(self.active_validators))
        slot = int(current_time / self.block_interval) % len(active_list)
        return active_list[slot]

class POHWithDPOS:
    """
    POH 和 DPOS 的集成系统
    """
    def __init__(self, poh, dpos):
        self.poh = poh
        self.dpos = dpos
        self.current_validator = None

    def produce_block(self, validator_address: str, transactions: List[str]) -> bool:
        """
        生成新区块
        """
        if validator_address not in self.dpos.active_validators:
            return False
            
        # 检查是否是当前验证者的出块时间
        expected_validator = self.dpos.get_next_block_validator()
        if validator_address != expected_validator:
            return False
            
        # 将交易打包到 POH 中
        for tx in transactions:
            self.poh.tick(tx)
            
        # 更新验证者的出块时间
        self.dpos.validators[validator_address].last_block_time = time.time()
        return True

class ConsensusEngine:
    def __init__(self, poh, dpos):
        self.poh = poh
        self.dpos = dpos
        self.blocks: List[Block] = []
        self.pending_blocks: Dict[int, List[Block]] = {}  # 待确认的区块
        self.confirmed_blocks: Dict[int, Block] = {}      # 已确认的区块
        
    def create_block(self, validator: str, transactions: List[str]) -> Block:
        """创建新区块"""
        height = len(self.blocks)
        previous_hash = self.blocks[-1].hash if self.blocks else "0" * 64
        
        # 将交易记录到POH中
        poh_hash = self.poh.tick(str(transactions)).hash
        
        block = Block(
            height=height,
            timestamp=time.time(),
            previous_hash=previous_hash,
            transactions=transactions,
            validator=validator,
            signature="",  # 需要验证者签名
            poh_hash=poh_hash
        )
        return block

class ForkChoice:
    """分叉选择"""
    def __init__(self):
        self.chains: Dict[str, List[Block]] = {}  # 不同的链
        self.head: str = ""  # 当前最长链的ID
        
    def add_block(self, block: Block) -> bool:
        """添加新区块，处理可能的分叉"""
        chain_id = block.previous_hash
        
        if chain_id not in self.chains:
            self.chains[chain_id] = []
            
        self.chains[chain_id].append(block)
        
        # 选择最长的有效链
        self.select_best_chain()
        return True
        
    def select_best_chain(self):
        """选择最长的有效链作为主链"""
        max_length = 0
        best_chain = ""
        
        for chain_id, chain in self.chains.items():
            if len(chain) > max_length and self.is_valid_chain(chain):
                max_length = len(chain)
                best_chain = chain_id
                
        self.head = best_chain

    def is_valid_chain(self, chain: List[Block]) -> bool:
        """验证链的有效性"""
        if not chain:
            return False
            
        # 验证区块连接
        for i in range(1, len(chain)):
            current_block = chain[i]
            previous_block = chain[i-1]
            
            # 验证区块高度连续性
            if current_block.height != previous_block.height + 1:
                return False
                
            # 验证区块链接关系
            if current_block.previous_hash != previous_block.hash:
                return False
                
        return True

class BlockConfirmation:
    """区块确认机制"""
    def __init__(self, required_confirmations: int = 3):
        self.required_confirmations = required_confirmations
        self.block_votes: Dict[str, Set[str]] = {}  # 区块哈希 -> 验证者集合
        
    def vote_block(self, block_hash: str, validator: str) -> bool:
        """验证者对区块投票"""
        if block_hash not in self.block_votes:
            self.block_votes[block_hash] = set()
            
        # 添加投票
        self.block_votes[block_hash].add(validator)
        
        # 返回是否达到确认条件
        return self.is_block_confirmed(block_hash)
        
    def is_block_confirmed(self, block_hash: str) -> bool:
        """检查区块是否已得到足够确认"""
        if block_hash not in self.block_votes:
            return False
            
        # 检查投票数量是否达到要求
        votes_count = len(self.block_votes[block_hash])
        print(f"当前投票数: {votes_count}, 需要投票数: {self.required_confirmations}")  # 添加调试信息
        return votes_count >= self.required_confirmations

    def get_block_votes(self, block_hash: str) -> int:
        """获取区块的投票数"""
        if block_hash not in self.block_votes:
            return 0
        return len(self.block_votes[block_hash])

class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = time.time()
        self.block_metrics: List[BlockMetrics] = []
        self.system_metrics: List[SystemMetrics] = []
        self.transaction_latencies: List[float] = []
        
    def record_block_metrics(self, metrics: BlockMetrics):
        """记录区块性能指标"""
        self.block_metrics.append(metrics)
        
    def record_transaction_latency(self, latency: float):
        """记录交易延迟"""
        self.transaction_latencies.append(latency)
        
    def collect_system_metrics(self):
        """收集系统性能指标"""
        metrics = SystemMetrics(
            cpu_usage=psutil.cpu_percent(),
            memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            network_io=dict(psutil.net_io_counters()._asdict()),
            timestamp=time.time()
        )
        self.system_metrics.append(metrics)
        
    def generate_report(self) -> dict:
        """生成性能报告"""
        if not self.block_metrics:
            return {}
            
        total_time = time.time() - self.start_time
        total_transactions = sum(m.transactions_count for m in self.block_metrics)
        
        return {
            "tps": total_transactions / total_time if total_time > 0 else 0,
            "average_latency": statistics.mean(self.transaction_latencies) if self.transaction_latencies else 0,
            "avg_cpu_usage": statistics.mean(m.cpu_usage for m in self.system_metrics) if self.system_metrics else 0,
            "avg_memory_usage": statistics.mean(m.memory_usage for m in self.system_metrics) if self.system_metrics else 0,
            "block_count": len(self.block_metrics),
            "total_transactions": total_transactions
        }

class ConsensusSystem:
    """完整的共识系统"""
    def __init__(self, poh, dpos):
        self.poh = poh
        self.dpos = dpos
        self.network = P2PNetwork()
        self.fork_choice = ForkChoice()
        self.confirmation = BlockConfirmation()
        self.blockchain = Blockchain()
        self.performance_monitor = PerformanceMonitor()
        self.transaction_pool = TransactionPool()

    def create_block(self, validator: str, transactions: List[str]) -> Block:
        """创建新区块"""
        start_time = time.time()
        latest_block = self.blockchain.get_latest_block()
        poh_hash = self.poh.tick(str(transactions)).hash
        
        block = Block(
            height=latest_block.height + 1 if latest_block else 0,
            timestamp=time.time(),
            previous_hash=latest_block.hash if latest_block else "0" * 64,
            transactions=transactions,
            validator=validator,
            signature="",  # 需要验证者签名
            poh_hash=poh_hash
        )
        
        # 录区块指标
        metrics = BlockMetrics(
            block_height=block.height,
            transactions_count=len(transactions),
            creation_time=time.time() - start_time,
            confirmation_time=0,  # 将在确认时更新
            validator=validator
        )
        self.performance_monitor.record_block_metrics(metrics)
        self.blockchain.add_block(block)
        return block

    async def run(self):
        """运行共识系统"""
        while True:
            # 处理网络消息
            await self.process_messages()
            
            # 如果是当前验证者，创建区块
            if self.is_current_validator():
                block = self.create_new_block()
                self.network.broadcast(
                    NetworkMessage("NEW_BLOCK", {"block": block})
                )
                
            # 处分叉
            self.fork_choice.select_best_chain()
            
            # 确认区块
            self.process_confirmations()
            
            await asyncio.sleep(1)

    async def process_transactions(self, transactions: List[str]):
        # 批量创建交易对象并直接处理
        txs = [
            Transaction(
                tx_id=f"tx_{time.time()}_{hash(tx_data)}",
                data=tx_data,
                timestamp=time.time(),
                gas_price=1.0,
                size=len(tx_data.encode())
            )
            for tx_data in transactions
        ]
        
        # 并行处理交易
        chunk_size = 5000  # 增加批处理大小
        tasks = []
        
        for i in range(0, len(txs), chunk_size):
            chunk = txs[i:i + chunk_size]
            task = asyncio.create_task(self._process_chunk(chunk))
            tasks.append(task)
            
        await asyncio.gather(*tasks)
        
        # 记录到POH中 (仅记录交易哈希,不做复杂计算)
        self.poh.tick(str([tx.tx_id for tx in txs]))

    async def _process_chunk(self, chunk: List[Transaction]):
        """处理交易批次"""
        for tx in chunk:
            # 将交易数据记录到POH中
            self.poh.tick(tx.data)
            
            # 这里可以添加其他交易处理逻辑
            # 例如: 状态更新、验证等
            
        return True

class ProofOfHistory:
    def __init__(self, difficulty: int = 4):  # 降低难度
        self.difficulty = difficulty
        self.history = []
        self._buffer_size = 1000  # 添加缓冲区
        self._hash_buffer = {}
        
    def _hash(self, previous_hash: str, data: Optional[str] = None) -> str:
        # 使用缓冲区加速重复哈希计算
        key = f"{previous_hash}:{data}"
        if key in self._hash_buffer:
            return self._hash_buffer[key]
            
        result = super()._hash(previous_hash, data)
        if len(self._hash_buffer) < self._buffer_size:
            self._hash_buffer[key] = result
        return result

# 使用示例
def demo_poh_dpos():
    from poh import ProofOfHistory  # 导入之前实现的 POH
    
    poh = ProofOfHistory(difficulty=3)
    dpos = DPOS(max_validators=3, block_interval=3)
    system = POHWithDPOS(poh, dpos)
    
    # 注册一些验证者
    validators = ["validator1", "validator2", "validator3", "validator4"]
    for v in validators:
        dpos.stake(v, 1000)  # 质押代币
        dpos.register_validator(v)
        
    # 进行一些投票
    dpos.vote("validator1", "validator2", 500)
    dpos.vote("validator2", "validator3", 300)
    dpos.vote("validator3", "validator1", 400)
    
    # 更新活跃验证者
    dpos.update_active_validators()
    
    # 模拟出块
    current_validator = dpos.get_next_block_validator()
    transactions = ["tx1", "tx2", "tx3"]
    success = system.produce_block(current_validator, transactions)
    
    print(f"Block production successful: {success}")
    print(f"Active validators: {dpos.active_validators}")
    print(f"Current validator: {current_validator}")

if __name__ == "__main__":
    demo_poh_dpos() 