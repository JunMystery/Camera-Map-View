"""Device type and preset variant definitions."""

from config.i18n import t

DEVICE_KIND_CAMERA = "Camera"
DEVICE_KIND_SERVER = "Server"
DEVICE_KIND_SWITCH = "Switch"
DEVICE_KIND_HUB = "Hub"
DEVICE_KIND_DVR = "DVR"
DEVICE_KIND_AP = "AP"
DEVICE_KIND_ROUTER = "Router"
DEVICE_KIND_FIREWALL = "Firewall"
DEVICE_KIND_PC = "PC"

DEVICE_KINDS = [
    DEVICE_KIND_CAMERA,
    DEVICE_KIND_SERVER,
    DEVICE_KIND_SWITCH,
    DEVICE_KIND_HUB,
    DEVICE_KIND_DVR,
    DEVICE_KIND_AP,
    DEVICE_KIND_ROUTER,
    DEVICE_KIND_FIREWALL,
    DEVICE_KIND_PC,
]

DEVICE_VARIANTS = {
    DEVICE_KIND_CAMERA: ["Fixed", "PTZ", "Dome", "Fisheye", "360", "AI"],
    DEVICE_KIND_SERVER: ["Rack", "Tower", "NAS", "NVR", "Workstation"],
    DEVICE_KIND_SWITCH: ["Core", "Distribution", "Access", "PoE", "Managed", "Unmanaged"],
    DEVICE_KIND_HUB: ["Ethernet Hub", "USB Hub", "Patch Hub"],
    DEVICE_KIND_DVR: ["DVR", "NVR", "Hybrid DVR"],
    DEVICE_KIND_AP: ["Indoor AP", "Outdoor AP", "Ceiling AP", "Mesh AP"],
    DEVICE_KIND_ROUTER: ["Edge Router", "WiFi Router", "VPN Router"],
    DEVICE_KIND_FIREWALL: ["UTM", "NGFW", "Hardware Firewall", "Virtual Firewall"],
    DEVICE_KIND_PC: ["PC", "Laptop", "Workstation"],
}


def device_kind_label(kind: str) -> str:
    """Return a translated label for a device kind."""
    key = kind.lower().replace(" ", "_")
    return t(f"device_kind.{key}")


def device_variant_label(variant: str) -> str:
    """Return a translated label for a preset device variant."""
    key = variant.lower().replace(" ", "_").replace("-", "_")
    return t(f"device_variant.{key}")


def variants_for_kind(kind: str) -> list[str]:
    """Return valid preset variants for one device kind."""
    return DEVICE_VARIANTS.get(kind, DEVICE_VARIANTS[DEVICE_KIND_CAMERA])
