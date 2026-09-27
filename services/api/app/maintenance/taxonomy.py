"""Controlled maintenance taxonomy. AI never mutates this catalog."""

from __future__ import annotations

from typing import Any

# LOCKED system → component hierarchy (DESIGN §9). Values are stable API keys.
SYSTEMS: dict[str, str] = {
    "engine": "Engine",
    "fuel_intake": "Fuel / Intake",
    "drivetrain": "Drivetrain",
    "brakes": "Brakes",
    "cooling": "Cooling",
    "suspension_chassis": "Suspension / Chassis",
    "electrical": "Electrical",
    "wheels_tires": "Wheels / Tires",
    "controls": "Controls",
    "other": "Other",
}

# Starter components per system (labels only — not mechanical specifications).
COMPONENTS: dict[str, dict[str, str]] = {
    "engine": {
        "engine_oil": "Engine oil / premix",
        "transmission_oil": "Transmission oil",
        "piston": "Piston",
        "cylinder": "Cylinder",
        "cylinder_head": "Cylinder head",
        "reed_valve": "Reed valve",
        "clutch": "Clutch",
        "air_filter": "Air filter",
        "spark_plug": "Spark plug",
        "other": "Other",
    },
    "fuel_intake": {
        "carburetor": "Carburetor",
        "fuel_tank": "Fuel tank",
        "fuel_filter": "Fuel filter",
        "throttle": "Throttle",
        "other": "Other",
    },
    "drivetrain": {
        "chain": "Chain",
        "sprocket": "Sprocket",
        "drive_shaft": "Drive shaft",
        "other": "Other",
    },
    "brakes": {
        "front_brake": "Front brake",
        "rear_brake": "Rear brake",
        "brake_pads": "Brake pads",
        "brake_fluid": "Brake fluid",
        "other": "Other",
    },
    "cooling": {
        "radiator": "Radiator",
        "coolant": "Coolant",
        "water_pump": "Water pump",
        "other": "Other",
    },
    "suspension_chassis": {
        "front_fork": "Front fork",
        "rear_shock": "Rear shock",
        "linkage": "Linkage",
        "frame": "Frame",
        "other": "Other",
    },
    "electrical": {
        "battery": "Battery",
        "wiring": "Wiring",
        "ignition": "Ignition",
        "lights": "Lights",
        "other": "Other",
    },
    "wheels_tires": {
        "front_tire": "Front tire",
        "rear_tire": "Rear tire",
        "wheel_bearings": "Wheel bearings",
        "spokes": "Spokes",
        "other": "Other",
    },
    "controls": {
        "handlebars": "Handlebars",
        "levers": "Levers",
        "cables": "Cables",
        "foot_controls": "Foot controls",
        "other": "Other",
    },
    "other": {
        "other": "Other",
    },
}

ACTIONS: dict[str, str] = {
    "inspect": "Inspect",
    "clean": "Clean",
    "lubricate": "Lubricate",
    "adjust": "Adjust",
    "tighten": "Tighten",
    "replace": "Replace",
    "repair": "Repair",
    "rebuild": "Rebuild",
    "service": "Service",
    "flush": "Flush",
    "bleed": "Bleed",
    "install": "Install",
    "remove": "Remove",
}

REASONS: dict[str, str] = {
    "scheduled": "Scheduled",
    "preventive": "Preventive",
    "post_ride": "Post-ride",
    "diagnostic": "Diagnostic",
    "repair": "Repair",
    "failure": "Failure",
    "modification_related": "Modification-related",
    "damage": "Damage",
    "other": "Other",
}

PERFORMER_TYPES: dict[str, str] = {
    "owner": "Owner",
    "shop": "Shop",
    "dealer": "Dealer",
    "previous_owner": "Previous owner",
    "other": "Other",
}

EVIDENCE_TYPES: dict[str, str] = {
    "owner_reported": "Owner reported",
    "photo_supported": "Photo supported",
    "receipt_supported": "Receipt supported",
    "shop_documented": "Shop documented",
}


class InvalidTaxonomy(ValueError):
    pass


def catalog() -> dict[str, Any]:
    return {
        "systems": [
            {"key": key, "label": label, "components": [
                {"key": ckey, "label": clabel}
                for ckey, clabel in COMPONENTS[key].items()
            ]}
            for key, label in SYSTEMS.items()
        ],
        "actions": [{"key": k, "label": v} for k, v in ACTIONS.items()],
        "reasons": [{"key": k, "label": v} for k, v in REASONS.items()],
        "performer_types": [{"key": k, "label": v} for k, v in PERFORMER_TYPES.items()],
        "evidence_types": [{"key": k, "label": v} for k, v in EVIDENCE_TYPES.items()],
    }


def validate_record_fields(
    *,
    system: str,
    component: str,
    component_detail: str | None,
    action: str,
    reason: str,
    performer_type: str,
    evidence_type: str,
) -> None:
    if system not in SYSTEMS:
        raise InvalidTaxonomy("Unknown maintenance system.")
    components = COMPONENTS.get(system) or {}
    if component not in components:
        raise InvalidTaxonomy("Unknown component for that system.")
    if action not in ACTIONS:
        raise InvalidTaxonomy("Unknown maintenance action.")
    if reason not in REASONS:
        raise InvalidTaxonomy("Unknown maintenance reason.")
    if performer_type not in PERFORMER_TYPES:
        raise InvalidTaxonomy("Unknown performer type.")
    if evidence_type not in EVIDENCE_TYPES:
        raise InvalidTaxonomy("Unknown evidence type.")
    detail = (component_detail or "").strip()
    if component == "other" and not detail:
        raise InvalidTaxonomy("Describe the component when selecting Other.")
    if component != "other" and detail:
        # Allow optional notes only for other; ignore/forbid stray detail on known keys.
        raise InvalidTaxonomy("Component detail is only used when component is Other.")


def is_other_component(component: str) -> bool:
    return component == "other"
