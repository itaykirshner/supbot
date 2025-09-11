"""
Zoho Desk Module for Slack Bot RAG
Provides integration with Zoho Desk API for ticket and conversation data
"""

from .zoho_desk_client import ZohoDeskClient
from .zoho_auth import ZohoDeskAuth
from .ticket_processor import TicketProcessor

__version__ = "1.0.0"
__all__ = ["ZohoDeskClient", "ZohoDeskAuth", "TicketProcessor"]
