"""
Distributed Consensus - Raft implementation using etcd.
Provides leader election, log replication, and state machine replication.
"""

import asyncio
import json
import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
try:
    import etcd3
except ImportError:
    etcd3 = None

logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuidv7() -> str:
    return str(uuid.uuid4())


# =============================================================================
# Consensus Models
# =============================================================================

class NodeState(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class ConsensusRole(str, Enum):
    VOTER = "voter"
    LEARNER = "learner"


@dataclass
class ClusterMember:
    member_id: str
    address: str
    role: ConsensusRole = ConsensusRole.VOTER
    priority: int = 1
    tags: Dict[str, str] = field(default_factory=dict)
    last_seen: Optional[datetime] = None


@dataclass
class LogEntry:
    term: int
    index: int
    command: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VoteRequest:
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass
class VoteResponse:
    term: int
    vote_granted: bool
    voter_id: str


@dataclass
class AppendEntriesRequest:
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[LogEntry]
    leader_commit: int


@dataclass
class AppendEntriesResponse:
    term: int
    success: bool
    match_index: int = 0


# =============================================================================
# Raft Consensus Engine
# =============================================================================

class RaftConsensus:
    """Raft consensus implementation using etcd for coordination.

    =========================================================
    SAFETY GATE (2026-08-25 institutional audit)
    DISABLED by default. Audit found:
      (a) heartbeat loop attribute never defined -> leader goes silent
      (b) undefined `request` variable in append handling -> NameError
      (c) _persist_state swallows datetime-JSON TypeError -> term/vote/log
          never persisted -> double-vote after restart => SPLIT BRAIN
      (d) propose() returns True on timeout => false durability acks
    A split-brain consensus layer is WORSE than none.
    Override (at your own risk): SWARM_ENABLE_UNSAFE_RAFT=1
    =========================================================
    """

    def __init__(
        self,
        member_id: str,
        cluster_members: List[ClusterMember],
        etcd_host: str = "localhost",
        etcd_port: int = 2379,
        election_timeout_ms: int = 150,
        heartbeat_interval_ms: int = 50,
    ):
        import os as _os
        if _os.environ.get("SWARM_ENABLE_UNSAFE_RAFT") != "1":
            raise RuntimeError(
                "RaftConsensus is disabled by institutional audit "
                "(split-brain risk). Fix known defects first and set "
                "SWARM_ENABLE_UNSAFE_RAFT=1 to override."
            )
        self.member_id = member_id
        self.cluster_members = {m.member_id: m for m in cluster_members}
        self.etcd_host = etcd_host
        self.etcd_port = etcd_port
        
        # Timing
        self.election_timeout_ms = election_timeout_ms
        self.heartbeat_interval_ms = heartbeat_interval_ms
        
        # State
        self.state = NodeState.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0
        
        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}
        
        # etcd client
        self._etcd_client: Optional[etcd3.Etcd3Client] = None
        
        # Timers
        self._election_timer: Optional[asyncio.Task] = None
        self._heartbeat_timer: Optional[asyncio.Task] = None
        self._running = False
        
        # State machine
        self._state_machine: Dict[str, Any] = {}
        self._apply_callback: Optional[Callable[[LogEntry], Any]] = None
        
        # Callbacks
        self._on_become_leader: Optional[Callable[[], None]] = None
        self._on_become_follower: Optional[Callable[[], None]] = None
        self._on_log_replicated: Optional[Callable[[LogEntry], None]] = None
        
        # Lock
        self._lock = asyncio.Lock()
    
    async def _get_etcd_client(self):
        if etcd3 is None:
            raise RuntimeError("etcd3 not installed. Install with: pip install etcd3")
        if self._etcd_client is None:
            self._etcd_client = etcd3.client(
                host="localhost",
                port=2379,
            )
        return self._etcd_client
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self) -> None:
        """Start the Raft node."""
        self._running = True
        self._reset_election_timer()
        logger.info(f"Raft node {self.member_id} started as {self.state.value}")
    
    async def stop(self) -> None:
        """Stop the Raft node."""
        self._running = False
        self._cancel_timers()
        if self._etcd_client:
            self._etcd_client.close()
    
    def _cancel_timers(self) -> None:
        for timer in [self._election_timer, self._heartbeat_timer]:
            if timer and not timer.done():
                timer.cancel()
    
    def _reset_election_timer(self) -> None:
        """Reset election timeout with random jitter."""
        self._cancel_election_timer()
        
        # Random timeout between election_timeout and 2*election_timeout
        import random
        timeout_ms = random.randint(
            self.election_timeout_ms,
            self.election_timeout_ms * 2
        )
        
        self._election_timer = asyncio.create_task(self._election_timeout(timeout_ms / 1000))
    
    def _cancel_election_timer(self) -> None:
        if self._election_timer and not self._election_timer.done():
            self._election_timer.cancel()
    
    async def _election_timeout(self, timeout_seconds: float) -> None:
        """Handle election timeout."""
        await asyncio.sleep(timeout_seconds)
        
        if not self._running:
            return
        
        async with self._lock:
            if self.state != NodeState.LEADER:
                await self._start_election()
    
    def _cancel_election_timer(self) -> None:
        if self._election_timer and not self._election_timer.done():
            self._election_timer.cancel()
    
    # =========================================================================
    # Leader Election
    # =========================================================================
    
    async def _start_election(self) -> None:
        """Start leader election."""
        logger.info(f"Node {self.member_id} starting election for term {self.current_term + 1}")
        
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.member_id
        
        # Persist term and vote
        await self._persist_state()
        
        # Request votes from other nodes
        vote_count = 1  # Vote for self
        last_log_index = len(self.log) - 1
        last_log_term = self.log[-1].term if self.log else 0
        
        # Request votes in parallel
        vote_tasks = []
        for member_id, member in self.cluster_members.items():
            if member_id != self.member_id:
                task = asyncio.create_task(self._request_vote(member_id, last_log_index, last_log_term))
                vote_tasks.append((member_id, task))
        
        # Collect votes
        for member_id, task in vote_tasks:
            try:
                granted = await task
                if granted:
                    vote_count += 1
            except Exception as e:
                logger.warning(f"Vote request to {member_id} failed: {e}")
        
        # Check if won election
        majority = len(self.cluster_members) // 2 + 1
        if vote_count >= majority:
            await self._become_leader()
        else:
            self.state = NodeState.FOLLOWER
            self._reset_election_timer()
    
    async def _request_vote(self, member_id: str, last_log_index: int, last_log_term: int) -> bool:
        """Request vote from a cluster member."""
        try:
            client = await self._get_etcd_client()
            
            # Use etcd for vote request
            vote_key = f"/raft/vote/{self.current_term}/{self.member_id}/{member_id}"
            
            vote_request = {
                "term": self.current_term,
                "candidate_id": self.member_id,
                "last_log_index": last_log_index,
                "last_log_term": last_log_term,
            }
            
            # Use etcd transaction for atomic vote
            success, _ = client.txn(
                compare=[client.transactions.version(vote_key) == 0],
                success=[client.put(vote_key, json.dumps(vote_request))],
                failure=[]
            )
            
            if not success:
                return False
            
            # Wait for response (in production, use watch)
            await asyncio.sleep(0.1)
            
            response_key = f"{vote_key}/response"
            response_data, _ = client.get(vote_key)
            
            if response_data:
                response = json.loads(response_data)
                return response.get("vote_granted", False)
            
            return False
            
        except Exception as e:
            logger.warning(f"Vote request to {member_id} failed: {e}")
            return False
    
    async def _handle_vote_request(self, request: VoteRequest) -> VoteResponse:
        """Handle incoming vote request."""
        async with self._lock:
            # Grant vote if:
            # 1. Term >= current term
            # 2. Haven't voted for someone else in this term
            # 2. Candidate's log is at least as up-to-date
            
            if request.term < self.current_term:
                return VoteResponse(
                    term=self.current_term,
                    vote_granted=False,
                    voter_id=self.member_id
                )
            
            if request.term > self.current_term:
                self.current_term = request.term
                self.state = NodeState.FOLLOWER
                self.voted_for = None
                await self._persist_state()
            
            # Check log up-to-date
            last_log_term = self.log[-1].term if self.log else 0
            last_log_index = len(self.log) - 1
            
            log_ok = (request.last_log_term > last_log_term or
                     (request.last_log_term == last_log_term and 
                      request.last_log_index >= last_log_index))
            
            vote_granted = (log_ok and 
                           (self.voted_for is None or self.voted_for == request.candidate_id))
            
            if vote_granted:
                self.voted_for = request.candidate_id
                self._reset_election_timer()
                await self._persist_state()
            
            return VoteResponse(
                term=self.current_term,
                vote_granted=vote_granted,
                voter_id=self.member_id
            )
    
    async def _become_leader(self) -> None:
        """Become leader."""
        logger.info(f"Node {self.member_id} became leader for term {self.current_term}")
        
        self.state = NodeState.LEADER
        self._cancel_election_timer()
        
        # Initialize leader state
        last_index = len(self.log)
        for member_id in self.cluster_members:
            if member_id != self.member_id:
                self.next_index[member_id] = len(self.log)
                self.match_index[member_id] = 0
        
        # Send initial heartbeat
        await self._send_heartbeats()
        
        # Start heartbeat timer
        self._heartbeat_timer = asyncio.create_task(self._heartbeat_loop())
        
        if self._on_become_leader:
            try:
                self._on_become_leader()
            except Exception as e:
                logger.error(f"Leader callback error: {e}")
    
    # =========================================================================
    # Log Replication
    # =========================================================================
    
    async def _send_heartbeats(self) -> None:
        """Send AppendEntries to all followers (heartbeat)."""
        for member_id in self.cluster_members:
            if member_id != self.member_id:
                asyncio.create_task(self._send_append_entries(member_id))
    
    async def _send_append_entries(self, member_id: str) -> None:
        """Send AppendEntries to a follower."""
        prev_log_index = self.next_index.get(member_id, 0) - 1
        prev_log_term = self.log[prev_log_index].term if prev_log_index >= 0 else 0
        
        entries = self.log[prev_log_index + 1:] if prev_log_index + 1 < len(self.log) else []
        
        request = AppendEntriesRequest(
            term=self.current_term,
            leader_id=self.member_id,
            prev_log_index=prev_log_index,
            prev_log_term=prev_log_term,
            entries=entries,
            leader_commit=self.commit_index,
        )
        
        try:
            response = await self._send_append_entries_rpc(member_id, request)
            await self._handle_append_entries_response(member_id, response)
        except Exception as e:
            logger.warning(f"AppendEntries to {member_id} failed: {e}")
    
    async def _send_append_entries_rpc(self, member_id: str, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """Send AppendEntries RPC to a follower."""
        # Use etcd for RPC
        client = await self._get_etcd_client()
        
        rpc_key = f"/raft/append/{self.current_term}/{self.member_id}/{member_id}"
        
        # Store request
        client.put(rpc_key, json.dumps(request.__dict__))
        
        # Wait for response (simplified)
        await asyncio.sleep(0.05)
        
        response_key = f"{rpc_key}/response"
        response_data, _ = client.get(response_key)
        
        if response_data:
            return AppendEntriesResponse(**json.loads(response_data))
        
        return AppendEntriesResponse(term=self.current_term, success=False)
    
    async def _handle_append_entries_response(self, member_id: str, response: AppendEntriesResponse) -> None:
        """Handle AppendEntries response."""
        async with self._lock:
            if response.term > self.current_term:
                self.current_term = response.term
                self.state = NodeState.FOLLOWER
                self.voted_for = None
                await self._persist_state()
                return
            
            if self.state != NodeState.LEADER:
                return
            
            if response.success:
                # Update nextIndex and matchIndex
                self.match_index[member_id] = max(
                    self.match_index.get(member_id, 0),
                    request.prev_log_index + len(request.entries)
                )
                self.next_index[member_id] = self.match_index[member_id] + 1
                
                # Check if we can advance commit index
                await self._update_commit_index()
            else:
                # Decrement nextIndex and retry
                self.next_index[member_id] = max(1, self.next_index.get(member_id, 1) - 1)
    
    async def _handle_append_entries(self, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """Handle incoming AppendEntries request."""
        async with self._lock:
            # Reply false if term < currentTerm
            if request.term < self.current_term:
                return AppendEntriesResponse(
                    term=self.current_term,
                    success=False
                )
            
            # If term > currentTerm, become follower
            if request.term > self.current_term:
                self.current_term = request.term
                self.state = NodeState.FOLLOWER
                self.voted_for = None
                await self._persist_state()
            
            # Reset election timer
            self._reset_election_timer()
            
            # Check log consistency
            if request.prev_log_index > 0:
                if request.prev_log_index >= len(self.log):
                    return AppendEntriesResponse(
                        term=self.current_term,
                        success=False
                    )
                
                if self.log[request.prev_log_index].term != request.prev_log_term:
                    return AppendEntriesResponse(
                        term=self.current_term,
                        success=False
                    )
            
            # Append new entries
            for i, entry in enumerate(request.entries):
                index = request.prev_log_index + 1 + i
                if index < len(self.log):
                    if self.log[index].term != entry.term:
                        self.log[index] = entry
                else:
                    self.log.append(entry)
            
            # Update commit index
            if request.leader_commit > self.commit_index:
                self.commit_index = min(request.leader_commit, len(self.log) - 1)
            
            return AppendEntriesResponse(
                term=self.current_term,
                success=True,
                match_index=len(self.log) - 1
            )
    
    async def _update_commit_index(self) -> None:
        """Update commit index based on majority replication."""
        for n in range(self.commit_index + 1, len(self.log)):
            # Count how many have replicated this entry
            count = 1  # Leader has it
            for member_id, match_idx in self.match_index.items():
                if match_idx >= n:
                    count += 1
            
            # Check if majority
            if count >= len(self.cluster_members) // 2 + 1:
                # Check term
                if self.log[n].term == self.current_term:
                    self.commit_index = n
                    await self._apply_committed_entries()
            else:
                break
    
    async def _apply_committed_entries(self) -> None:
        """Apply newly committed entries to state machine."""
        for i in range(self.last_applied + 1, self.commit_index + 1):
            entry = self.log[i]
            if self._apply_callback:
                try:
                    await self._apply_callback(entry)
                except Exception as e:
                    logger.error(f"Apply callback failed: {e}")
            self.last_applied = i
    
    # =========================================================================
    # Client API
    # =========================================================================
    
    async def propose(self, command: Dict[str, Any]) -> bool:
        """Propose a command for consensus."""
        async with self._lock:
            if self.state != NodeState.LEADER:
                return False
            
            entry = LogEntry(
                term=self.current_term,
                index=len(self.log),
                command=command,
            )
            
            self.log.append(entry)
            await self._send_heartbeats()
            
            # Wait for commitment (simplified)
            await self._wait_for_commit(len(self.log) - 1)
            return True
    
    async def _wait_for_commit(self, index: int, timeout: float = 5.0) -> bool:
        """Wait for an entry to be committed."""
        start = time.time()
        while time.time() - start < timeout:
            if self.commit_index >= index:
                return True
            await asyncio.sleep(0.01)
        return False
    
    # =========================================================================
    # Persistence
    # =========================================================================
    
    async def _persist_state(self) -> None:
        """Persist Raft state to etcd."""
        try:
            client = await self._get_etcd_client()
            
            state_data = {
                "term": self.current_term,
                "voted_for": self.voted_for,
                "log": [e.__dict__ for e in self.log],
                "commit_index": self.commit_index,
            }
            
            client.put(f"/raft/state/{self.member_id}", json.dumps(state_data))
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")
    
    async def _load_state(self) -> None:
        """Load Raft state from etcd."""
        try:
            client = await self._get_etcd_client()
            data, _ = client.get(f"/raft/state/{self.member_id}")
            
            if data:
                state = json.loads(data)
                self.current_term = state.get("term", 0)
                self.voted_for = state.get("voted_for")
                self.log = [LogEntry(**e) for e in state.get("log", [])]
                self.commit_index = state.get("commit_index", 0)
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    async def _get_etcd_client(self):
        if etcd3 is None:
            raise RuntimeError("etcd3 not installed. Install with: pip install etcd3")
        if self._etcd_client is None:
            self._etcd_client = etcd3.client(
                host="localhost",
                port=2379,
            )
        return self._etcd_client
    
    def set_apply_callback(self, callback: Callable[[LogEntry], Any]) -> None:
        self._apply_callback = callback
    
    def set_leader_callback(self, callback: Callable[[], None]) -> None:
        self._on_become_leader = callback
    
    def set_follower_callback(self, callback: Callable[[], None]) -> None:
        self._on_become_follower = callback
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "member_id": self.member_id,
            "state": self.state.value,
            "term": self.current_term,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "leader": self._get_leader_id(),
        }
    
    def _get_leader_id(self) -> Optional[str]:
        if self.state == NodeState.LEADER:
            return self.member_id
        return None


# =============================================================================
# Consensus Manager (High-level API)
# =============================================================================

class ConsensusManager:
    """High-level consensus management."""
    
    def __init__(
        self,
        member_id: str,
        cluster_members: List[ClusterMember],
        etcd_host: str = "localhost",
        etcd_port: int = 2379,
    ):
        self.raft = RaftConsensus(
            member_id=member_id,
            cluster_members=cluster_members,
            etcd_host=etcd_host,
            etcd_port=etcd_port,
        )
    
    async def start(self) -> None:
        await self.raft.start()
    
    async def stop(self) -> None:
        await self.raft.stop()
    
    async def propose(self, command: Dict[str, Any]) -> bool:
        """Propose a command for consensus."""
        return await self.raft.propose(command)
    
    def set_state_machine_callback(self, callback: Callable[[LogEntry], Any]) -> None:
        self.raft.set_apply_callback(callback)
    
    def get_status(self) -> Dict[str, Any]:
        return self.raft.get_status()


# =============================================================================
# Factory
# =============================================================================

def create_consensus_manager(
    member_id: str,
    cluster_members: List[ClusterMember],
    etcd_host: str = "localhost",
    etcd_port: int = 2379,
) -> ConsensusManager:
    return ConsensusManager(member_id, cluster_members, etcd_host, etcd_port)
