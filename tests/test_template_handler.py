from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from lrm_operator.handlers.template import _create_child_resource, _create_generated_resources
from lrm_operator.models import LockableResourceTemplateSpec

TEMPLATE_BODY = {
    "metadata": {
        "name": "my-template",
        "uid": "abc-123",
    }
}


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
            await _create_child_resource("child-0", "default", TEMPLATE_BODY, spec, AsyncMock())
            mock_create.assert_called_once()
            body = mock_create.call_args.kwargs.get("body")
            assert body["metadata"]["name"] == "child-0"
            assert "lrm.openlab.io/main-label" in body["metadata"]["labels"]

    @pytest.mark.asyncio
    async def test_adds_owner_references(self):
        spec = LockableResourceTemplateSpec(type="generated", number=1)

        with (
            patch(
                "lrm_operator.handlers.template.CUSTOM_API.create_namespaced_custom_object",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            await _create_child_resource("child-0", "default", TEMPLATE_BODY, spec, AsyncMock())
            body = mock_create.call_args.kwargs.get("body")
            owner_refs = body["metadata"]["ownerReferences"]
            assert len(owner_refs) == 1
            assert owner_refs[0]["name"] == "my-template"
            assert owner_refs[0]["uid"] == "abc-123"
            assert owner_refs[0]["kind"] == "LockableResourceTemplate"


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
            await _create_generated_resources("tmpl", "default", TEMPLATE_BODY, spec, AsyncMock())
            assert mock_create.call_count == 3
            names = [
                mock_create.call_args_list[i].kwargs.get("body", {}).get("metadata", {}).get("name")
                for i in range(mock_create.call_count)
            ]
            assert "tmpl-0" in names
            assert "tmpl-1" in names
            assert "tmpl-2" in names
