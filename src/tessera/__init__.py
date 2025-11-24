"""
Autonomy: Multi-agent AI framework with Supervisor and Interviewer personas.
"""

from .copilot_proxy import CopilotProxyManager, is_proxy_running, start_proxy, stop_proxy
from .interviewer import InterviewerAgent
from .models import AgentResponse, InterviewResult, PanelResult, Task
from .panel import PanelSystem
from .supervisor import SupervisorAgent

__version__ = "0.1.0"

__all__ = [
    "AgentResponse",
    "CopilotProxyManager",
    "InterviewResult",
    "InterviewerAgent",
    "PanelResult",
    "PanelSystem",
    "SupervisorAgent",
    "Task",
    "is_proxy_running",
    "start_proxy",
    "stop_proxy",
]
