from __future__ import annotations

import kopf


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.peering.standalone = False


@kopf.on.cleanup()
def shutdown(logger, **_):
    logger.info("LRM Operator shutting down.")


@kopf.on.probe(id="liveness")
def liveness(**_):
    return "ok"


@kopf.on.probe(id="readiness")
def readiness(**_):
    return "ok"
