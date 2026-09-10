"""components.agent — Universal Model Context Protocol (MCP) surface for Uniti.

Exposes domain-agnostic generic tools over the Graph (LinkML ontology),
Operational Database (projections & digital twin), and Kernel (immutable append-only log).
"""

from .tools import UnitiTools

__all__ = ["UnitiTools"]
