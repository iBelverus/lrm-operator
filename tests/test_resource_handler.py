from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from lrm_operator.handlers.resource import on_resource_create, on_resource_update
from lrm_operator.models import LockableResourceStatus


class TestResourceCreate:
    @pytest.mark.asyncio
    async def test_initializes_with_free_phase(self):
        body = {
            "metadata": {"name": "res-1", "namespace": "default"},
            "spec": {"templateRef": {"name": "tpl"}},
        }
        spec = body["spec"]
        status = {}
        logger = AsyncMock()

        with patch(
            "lrm_operator.handlers.resource._update_resource_status", new_callable=AsyncMock
        ) as mock_update:
            await on_resource_create(body, spec, status, "res-1", "default", logger)
            mock_update.assert_called_once()
            _, _, resource_status, _ = mock_update.call_args[0]
            assert isinstance(resource_status, LockableResourceStatus)
            assert resource_status.phase == "free"


class TestResourceUpdate:
    @pytest.mark.asyncio
    async def test_valid_transition(self):
        body = {"metadata": {"name": "res-1", "namespace": "default"}}
        spec = {}
        status = {"phase": "free"}
        old = {}
        new = {"status": {"phase": "locked"}}
        logger = AsyncMock()

        with patch(
            "lrm_operator.handlers.resource._update_resource_status", new_callable=AsyncMock
        ) as mock_update:
            await on_resource_update(body, spec, status, old, new, "res-1", "default", logger)
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_same_phase_no_update(self):
        body = {"metadata": {"name": "res-1", "namespace": "default"}}
        spec = {}
        status = {"phase": "free"}
        old = {}
        new = {"status": {"phase": "free"}}
        logger = AsyncMock()

        with patch(
            "lrm_operator.handlers.resource._update_resource_status", new_callable=AsyncMock
        ) as mock_update:
            await on_resource_update(body, spec, status, old, new, "res-1", "default", logger)
            mock_update.assert_not_called()
