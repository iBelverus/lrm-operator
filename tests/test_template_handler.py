from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from lrm_operator.handlers.template import _create_child_resource, _create_generated_resources
from lrm_operator.models import LockableResourceTemplateSpec


class TestTemplateCreateChildResource:
    @pytest.mark.asyncio
    async def test_creates_child_with_labels(self):
        spec = LockableResourceTemplateSpec(type="generated", number=1, main_label="test")

        with (
            patch(
                "lrm_operator.handlers.template.CUSTOM_API.create_namespaced_custom_object",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            await _create_child_resource("child-0", "default", spec, AsyncMock())
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            body = call_args.kwargs.get("body", call_args.args[0] if call_args.args else {})
            assert body["metadata"]["name"] == "child-0"
            assert "lrm.openlab.io/main-label" in body["metadata"]["labels"]


class TestTemplateCreateGeneratedResources:
    @pytest.mark.asyncio
    async def test_creates_n_children(self):
        spec = LockableResourceTemplateSpec(type="generated", number=3)

        with (
            patch(
                "lrm_operator.handlers.template.CUSTOM_API.create_namespaced_custom_object",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            await _create_generated_resources("tmpl", "default", spec, AsyncMock())
            assert mock_create.call_count == 3
            names = [
                call.kwargs.get("body", call.args[0] if call.args else {})
                .get("metadata", {})
                .get("name")
                for call in mock_create.call_args_list
            ]
            assert "tmpl-0" in names
            assert "tmpl-1" in names
            assert "tmpl-2" in names
