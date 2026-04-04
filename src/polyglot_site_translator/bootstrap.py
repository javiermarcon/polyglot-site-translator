"""Bootstrap helpers for the presentation shell."""

from __future__ import annotations

from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.router import FrontendRouter


def create_frontend_shell(services: FrontendServices) -> FrontendShell:
    """Create the presentation shell with a fresh router."""
    return FrontendShell(router=FrontendRouter(), services=services)
