from __future__ import annotations

import asyncio

import kopf
import kubernetes.client as k8s
import kubernetes

from ..models import (
    LockableResourceTemplateSpec,
    LockableResourceTemplateStatus,
)

API_GROUP = "lrm.openlab.io"
API_VERSION = "v1alpha1"
TEMPLATE_PLURAL = "lockableresourcetemplates"
RESOURCE_PLURAL = "lockableresources"

# Load in-cluster config when running inside a pod,
# or local kubeconfig during development
try:
    kubernetes.config.load_incluster_config()
except kubernetes.config.ConfigException:
    kubernetes.config.load_kube_config()

CUSTOM_API = k8s.CustomObjectsApi()


@kopf.on.create(API_GROUP, API_VERSION, TEMPLATE_PLURAL)
async def on_template_create(body, spec, name, namespace, logger, **kwargs):
    template_spec = LockableResourceTemplateSpec(**spec)
    logger.info(f"Template {name} created with type={template_spec.type}")

    if template_spec.type == "generated":
        await _create_generated_resources(name, namespace, body, template_spec, logger)
    elif template_spec.type == "static":
        await _create_static_resources(name, namespace, body, template_spec, logger)

    status = LockableResourceTemplateStatus(ready=True)
    await _update_template_status(name, namespace, status, logger)


@kopf.on.update(API_GROUP, API_VERSION, TEMPLATE_PLURAL)
async def on_template_update(body, spec, name, namespace, old, new, logger, **kwargs):
    template_spec = LockableResourceTemplateSpec(**spec)
    logger.info(f"Template {name} updated")

    if template_spec.type == "generated":
        await _create_generated_resources(name, namespace, body, template_spec, logger)
    elif template_spec.type == "static":
        await _create_static_resources(name, namespace, body, template_spec, logger)


@kopf.on.delete(API_GROUP, API_VERSION, TEMPLATE_PLURAL)
async def on_template_delete(body, name, namespace, logger, **kwargs):
    logger.info(
        f"Template {name} deleted — children will be garbage collected via owner references"
    )


async def _create_generated_resources(
    template_name: str,
    namespace: str,
    template_body: dict,
    template_spec: LockableResourceTemplateSpec,
    logger,
):
    count = template_spec.number or 1
    for i in range(count):
        child_name = f"{template_name}-{i}"
        await _create_child_resource(child_name, namespace, template_body, template_spec, logger)
    logger.info(f"Created {count} generated children for template {template_name}")


async def _create_static_resources(
    template_name: str,
    namespace: str,
    template_body: dict,
    template_spec: LockableResourceTemplateSpec,
    logger,
):
    if not template_spec.resource_list:
        return
    for item in template_spec.resource_list:
        await _create_child_resource(item.name, namespace, template_body, template_spec, logger)
    logger.info(
        f"Created {len(template_spec.resource_list)} static children for template {template_name}"
    )


async def _create_child_resource(
    child_name: str,
    namespace: str,
    template_body: dict,
    template_spec: LockableResourceTemplateSpec,
    logger,
):
    labels = template_spec.extra_labels.copy() if template_spec.extra_labels else {}
    if template_spec.main_label:
        labels["lrm.openlab.io/main-label"] = template_spec.main_label

    template_uid = template_body.get("metadata", {}).get("uid", "")
    template_name = template_body.get("metadata", {}).get("name", "")

    resource_body = {
        "apiVersion": f"{API_GROUP}/{API_VERSION}",
        "kind": "LockableResource",
        "metadata": {
            "name": child_name,
            "labels": labels,
            "annotations": {
                "lrm.openlab.io/template-ref": template_name,
            },
            "ownerReferences": [
                {
                    "apiVersion": f"{API_GROUP}/{API_VERSION}",
                    "kind": "LockableResourceTemplate",
                    "name": template_name,
                    "uid": template_uid,
                }
            ],
        },
        "spec": {
            "templateRef": {"name": template_name},
            "nodeSelector": template_spec.node_selector,
            "resources": template_spec.resources,
            "tolerations": template_spec.tolerations,
            "affinity": template_spec.affinity,
            "topologySpreadConstraints": template_spec.topology_spread_constraints,
            "serviceAccountName": template_spec.service_account_name,
            "priorityClassName": template_spec.priority_class_name,
            "schedulerName": template_spec.scheduler_name,
            "runtimeClassName": template_spec.runtime_class_name,
        },
    }

    try:
        await asyncio.to_thread(
            CUSTOM_API.create_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=RESOURCE_PLURAL,
            body=resource_body,
        )
    except k8s.exceptions.ApiException as e:
        if e.status == 409:
            logger.debug(f"Child resource {child_name} already exists, skipping")
        else:
            raise


async def _update_template_status(
    name: str,
    namespace: str,
    status: LockableResourceTemplateStatus,
    logger,
):
    try:
        existing = await asyncio.to_thread(
            CUSTOM_API.get_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=TEMPLATE_PLURAL,
            name=name,
        )
        existing["status"] = status.model_dump(by_alias=True, exclude_none=True)
        await asyncio.to_thread(
            CUSTOM_API.replace_namespaced_custom_object,
            group=API_GROUP,
            version=API_VERSION,
            namespace=namespace,
            plural=TEMPLATE_PLURAL,
            name=name,
            body=existing,
        )
    except k8s.exceptions.ApiException as e:
        logger.error(f"Failed to update template status: {e}")
