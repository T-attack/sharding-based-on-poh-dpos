from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import time
from network import NetworkMessage, P2PNetwork
from time_sharding import TimeShardingManager

@dataclass
class StateUpdate:
    """状态更新"""
    update_id: str
    shard_id: int
    data: dict
    timestamp: float
    version: int
    status: str = "pending"  # pending, syncing, completed

class StateSyncManager:
    def __init__(self, 
                 time_sharding: TimeShardingManager,
                 network: P2PNetwork):
        self.time_sharding = time_sharding
        self.network = network
        self.state_versions: Dict[int, int] = {}  # 每个分片的状态版本
        self.pending_updates: Dict[str, StateUpdate] = {}
        self.completed_updates: Set[str] = set()
        self.state_cache: Dict[int, Dict] = {}  # 分片状态缓存
        
        # 初始化所有分片的状态
        for shard_id in range(self.time_sharding.shard_count):
            self.state_cache[shard_id] = {"balance": 0}
            self.state_versions[shard_id] = 0
        
    def update_state(self, shard_id: int, data: dict) -> str:
        """更新分片状态"""
        # 检查分片ID是否有效
        if shard_id >= self.time_sharding.shard_count:
            raise ValueError(f"无效的分片ID: {shard_id}")
            
        # 生成新的状态版本
        current_version = self.state_versions.get(shard_id, 0)
        new_version = current_version + 1
        
        # 创建状态更新
        update = StateUpdate(
            update_id=f"update_{time.time()}_{shard_id}_{new_version}",
            shard_id=shard_id,
            data=data,
            timestamp=time.time(),
            version=new_version
        )
        
        # 添加到待处理队列
        self.pending_updates[update.update_id] = update
        
        # 广播状态更新
        self.network.broadcast(NetworkMessage(
            "STATE_UPDATE",
            {"update": update}
        ))
        
        return update.update_id
        
    def sync_state(self, shard_id: int) -> bool:
        """同步分片状态"""
        try:
            # 检查分片ID是否有效
            if shard_id >= self.time_sharding.shard_count:
                return False
                
            # 获取待处理的状态更新
            updates = [
                update for update in self.pending_updates.values()
                if update.shard_id == shard_id
            ]
            
            # 按版本号排序
            updates.sort(key=lambda x: x.version)
            
            # 应用状态更新
            for update in updates:
                if self._apply_state_update(update):
                    self.completed_updates.add(update.update_id)
                    del self.pending_updates[update.update_id]
                    
            # 更新状态版本
            if updates:
                self.state_versions[shard_id] = updates[-1].version
                
            return True
            
        except Exception as e:
            print(f"同步分片 {shard_id} 状态时出错: {e}")
            return False
            
    def _apply_state_update(self, update: StateUpdate) -> bool:
        """应用状态更新"""
        try:
            # 检查版本
            current_version = self.state_versions.get(update.shard_id, 0)
            if update.version <= current_version:
                return False
                
            # 确保分片状态已初始化
            if update.shard_id not in self.state_cache:
                self.state_cache[update.shard_id] = {"balance": 0}
                
            # 更新状态
            self.state_cache[update.shard_id].update(update.data)
            update.status = "completed"
            
            return True
            
        except Exception as e:
            print(f"应用状态更新 {update.update_id} 时出错: {e}")
            return False
            
    def get_shard_state(self, shard_id: int) -> Optional[Dict]:
        """获取分片状态"""
        # 检查分片ID是否有效
        if shard_id >= self.time_sharding.shard_count:
            return None
            
        # 确保分片状态已初始化
        if shard_id not in self.state_cache:
            self.state_cache[shard_id] = {"balance": 0}
            
        return self.state_cache[shard_id] 