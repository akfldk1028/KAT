from typing import List, Optional
from .agents.outgoing import OutgoingAgent
from .agents.incoming import IncomingAgent

class AgentManager:
    _outgoing: Optional[OutgoingAgent] = None
    _incoming: Optional[IncomingAgent] = None

    @classmethod
    def get_outgoing(cls) -> OutgoingAgent:
        if cls._outgoing is None:
            print("[AgentManager] Creating instance of 'outgoing' agent...")
            cls._outgoing = OutgoingAgent()
        return cls._outgoing

    @classmethod
    def get_incoming(cls) -> IncomingAgent:
        if cls._incoming is None:
            print("[AgentManager] Creating instance of 'incoming' agent...")
            cls._incoming = IncomingAgent()
        return cls._incoming

    @classmethod
    def list_agents(cls) -> List[str]:
        return ["outgoing", "incoming"]
