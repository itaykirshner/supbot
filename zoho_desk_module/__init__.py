"""
Zoho Desk Module for Slack Bot RAG
Provides integration with Zoho Desk API for ticket and conversation data
"""

from zoho_desk_module.zoho_desk_client import ZohoDeskClient
from zoho_desk_module.zoho_auth import ZohoDeskAuth
from zoho_desk_module.ticket_processor import TicketProcessor

__version__ = "1.0.0"
__all__ = ["ZohoDeskClient", "ZohoDeskAuth", "TicketProcessor"]
