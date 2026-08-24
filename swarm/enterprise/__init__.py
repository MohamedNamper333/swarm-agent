"""Enterprise tier: Board, C-Suite, Directors, Workers.

Phase 1 (roadmap §6) ships 16 agents across:
- board/   — 5 strategic decision agents (chairman + 4 advisors)
- knowledge/ — 5 RAG/embedding agents (W2)
- safety/  — 4 safety dept agents + inline filter (W3)

Phase 2 (§7) adds C-Suite (7) + Code Dept (7).
Phase 3 (§8) adds Design/Video/Research/Data/Language (21).
"""

from .swarm_master import SwarmMaster, SwarmRequest, SwarmResult, get_master

__all__ = [
    "SwarmMaster",
    "SwarmRequest", 
    "SwarmResult",
    "get_master",
]
