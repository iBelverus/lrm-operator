from __future__ import annotations

import asyncio
import datetime

import kopf
import kubernetes.client as k8s

from ..models import LockableResourceStatus
from ..state_machine import VALID_PHASES, is_valid_transition, transition

API_GROUP = "lrm.openlab.io"
API_VERSION = "v1alpha1"
RESOURCE_PLURAL = "lockableresources"

CUSTOM_API = k8s.CustomObjectsApi()
CORE_API = k8s.CoreV1Api()

POD_ANNOTATION = "lrm.openlab.io/lockable-resource"


@kopf.on.create(API_GROUP, API_VERSION, RESOURCE_PLURAL)
async def on_resource_create(body, spec, status, name, namespace, logger, **kwargs):
    current_status = status or {}
    current_phase = current_status.get("phase", "free")

    if current_phase not in VALID_PHASES:
        current_phase = "free"

    resource_status = LockableResourceStatus(phase=current_phase)
    await _update_resource_status(name, namespace, resource_status, logger)
    logger.info(f"LockableResource {name} initialized with phase=free")


@kopf.on.update(API_GROUP, API_VERSION, RESOURCE_PLURAL)
async def on_resource_update(body, spec, status, old, new, name, namespace, logger, **kwargs):
    old_status = status or {}
    old_phase = old_status.get("phase", "free")
    new_phase = new.get("status", {}).get("phase", old_phase) if new else old_phase

    if old_phase == new_phase:
        return

    if not is_valid_transition(old_phase, new_phase):
        logger.warning(f"Invalid phase transition for {name}: {old_phase} → {new_phase}")
        raise kopf.TemporaryError(f"Invalid transition: {old_phase} → {new_phase}", delay=30)

    resource_status = LockableResourceStatus(**new.get("status", {}))
    logger.info(f"LockableResource {name} transitioned: {old_phase} → {new_phase}")
    await _update_resource_status(name, namespace, resource_status, logger)


@kopf.on.event("", "v1", "pods")
async def on_pod_event(event, body, name, namespace, logger, **kwargs):
    annotations = body.get("metadata", {}).get("annotations", {})
    resource_name = annotations.get(POD_ANNOTATION)

    if not resource_name:
        return

    logger.info(f"Pod {name} references lockable resource: {resource_name}")

    if event["type"] == "ADDED":
        if body.get("status", {}).get("phase") == "Running":
            await _acquire_lock(resource_name, namespace, name, logger)
    elif event["type"] == "DELETED":
        await _release_lock(resource_name, namespace, logger)


async def _acquire_lock(resource_name: str, namespace: str, pod_name: str, logger):
    try:
        existing = await asyncio.to_thread(
            CUSTOM_API.get_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=RESOURCE_PLURAL,
            name=resource_name,
        )

        current_phase = existing.get("status", {}).get("phase", "free")

        if current_phase != "free":
            logger.info(
                f"Resource {resource_name} is not free (phase={current_phase}), cannot acquire"
            )
            return

        result = transition("free", "pod_start")
        if result is None:
            logger.warning(f"Cannot transition resource {resource_name} from free to locked")
            return

        existing["status"] = {
            "phase": result,
            "podRef": {
                "name": pod_name,
                "namespace": namespace,
            },
            "lockedAt": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        await asyncio.to_thread(
            CUSTOM_API.replace_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=RESOURCE_PLURAL,
            name=resource_name,
            body=existing,
        )

        logger.info(f"Pod {pod_name} acquired lock on {resource_name}")
    except k8s.exceptions.ApiException as e:
        if e.status == 404:
            logger.warning(f"LockableResource {resource_name} not found")
        else:
            raise


async def _release_lock(resource_name: str, namespace: str, logger):
    try:
        existing = await asyncio.to_thread(
            CUSTOM_API.get_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=RESOURCE_PLURAL,
            name=resource_name,
        )

        current_status = existing.get("status", {})
        current_phase = current_status.get("phase", "free")

        if current_phase != "locked":
            return

        reserved_by = current_status.get("reservedBy")
        event = "pod_done_set" if reserved_by else "pod_done_nil"
        new_phase = transition("locked", event)

        if new_phase is None:
            return

        existing["status"] = {
            "phase": new_phase,
            "podRef": None,
            "lockedAt": None,
            "reservedBy": current_status.get("reservedBy"),
            "reservedAt": current_status.get("reservedAt"),
        }

        await asyncio.to_thread(
            CUSTOM_API.replace_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=RESOURCE_PLURAL,
            name=resource_name,
            body=existing,
        )

        logger.info(f"Lock released on {resource_name}, new phase={new_phase}")
    except k8s.exceptions.ApiException as e:
        if e.status == 404:
            logger.warning(f"LockableResource {resource_name} not found")
        else:
            raise


async def _update_resource_status(
    name: str,
    namespace: str,
    status: LockableResourceStatus,
    logger,
):
    try:
        existing = await asyncio.to_thread(
            CUSTOM_API.get_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=RESOURCE_PLURAL,
            name=name,
        )
        existing["status"] = status.model_dump(by_alias=True, exclude_none=True)
        await asyncio.to_thread(
            CUSTOM_API.replace_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=RESOURCE_PLURAL,
            name=name,
            body=existing,
        )
    except k8s.exceptions.ApiException as e:
        logger.error(f"Failed to update resource status: {e}")
