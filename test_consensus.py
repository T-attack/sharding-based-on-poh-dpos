import asyncio
import time
from poh import ProofOfHistory
from dpos import DPOS, POHWithDPOS, ConsensusSystem
from network import NetworkMessage, Node, P2PNetwork

async def test_consensus_system():
    print("开始测试共识系统...")
    
    # 1. 初始化系统
    poh = ProofOfHistory(difficulty=3)
    dpos = DPOS(max_validators=3, block_interval=3)
    consensus = ConsensusSystem(poh, dpos)
    
    # 2. 测试质押和验证者注册
    print("\n测试质押和验证者注册:")
    validators = ["validator1", "validator2", "validator3", "validator4"]
    stakes = [1000, 1500, 800, 1200]
    
    for v, s in zip(validators, stakes):
        success = dpos.stake(v, s)
        print(f"验证者 {v} 质押 {s} 代币: {'成功' if success else '失败'}")
        success = dpos.register_validator(v)
        print(f"验证者 {v} 注册: {'成功' if success else '失败'}")
    
    # 3. 测试投票机制
    print("\n测试投票机制:")
    votes = [
        ("validator1", "validator2", 500),
        ("validator2", "validator3", 300),
        ("validator3", "validator1", 400),
        ("validator4", "validator2", 600)
    ]
    
    for voter, candidate, amount in votes:
        success = dpos.vote(voter, candidate, amount)
        print(f"{voter} 给 {candidate} 投票 {amount}: {'成功' if success else '失败'}")
    
    # 4. 测试验证者选举
    print("\n测试验证者选举:")
    dpos.update_active_validators()
    print(f"活跃验证者列表: {dpos.active_validators}")
    
    # 5. 测试区块生成
    print("\n测试区块生成:")
    for i in range(3):
        current_validator = dpos.get_next_block_validator()
        transactions = [f"tx{i}_1", f"tx{i}_2", f"tx{i}_3"]
        
        # 创建新区块
        block = consensus.create_block(current_validator, transactions)
        print(f"区块 {i} 由验证者 {current_validator} 生成")
        print(f"区块内容: {block}")
        
        # 广播区块
        consensus.network.broadcast(
            NetworkMessage("NEW_BLOCK", {"block": block})
        )
        
        # 等待一个出块间隔
        await asyncio.sleep(dpos.block_interval)
    
    # 6. 测试分叉处理
    print("\n测试分叉处理:")
    fork_block = consensus.create_block(
        dpos.get_next_block_validator(),
        ["fork_tx1", "fork_tx2"]
    )
    consensus.fork_choice.add_block(fork_block)
    print(f"分叉链头: {consensus.fork_choice.head}")
    
    # 7. 测试区块确认
    print("\n测试区块确认:")
    block_hash = block.hash  # 使用最后生成的区块
    for validator in list(dpos.active_validators)[:3]:
        success = consensus.confirmation.vote_block(block_hash, validator)
        votes = consensus.confirmation.get_block_votes(block_hash)
        print(f"验证者 {validator} 确认区块: {'成功' if success else '失败'} (当前投票数: {votes})")
    
    is_confirmed = consensus.confirmation.is_block_confirmed(block_hash)
    print(f"区块确认状态: {'已确认' if is_confirmed else '未确认'}")
    
    # 8. 测试 POH 验证
    print("\n测试 POH 验证:")
    is_valid = poh.verify(0, len(poh.history) - 1)
    print(f"POH 历史记录验证: {'有效' if is_valid else '无效'}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_consensus_system()) 