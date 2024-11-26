import time
from typing import Dict, List

class NetworkMessage:
    """网络消息"""
    def __init__(self, msg_type: str, data: dict):
        self.type = msg_type
        self.data = data
        self.timestamp = time.time()

class Node:
    """网络节点"""
    def __init__(self, node_id: str):
        self.id = node_id
        self.messages: List[NetworkMessage] = []

    def receive_message(self, message: NetworkMessage):
        self.messages.append(message)

class P2PNetwork:
    """节点间通信网络"""
    def __init__(self):
        self.peers: Dict[str, Node] = {}
        self.message_queue: List[NetworkMessage] = []
        
    def broadcast(self, message: NetworkMessage):
        """广播消息到所有节点"""
        for peer in self.peers.values():
            peer.receive_message(message)
            
    def handle_message(self, message: NetworkMessage):
        """处理接收到的消息"""
        if message.type == "NEW_BLOCK":
            self.handle_new_block(message.data)
        elif message.type == "VOTE":
            self.handle_vote(message.data) 