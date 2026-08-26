import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List


class ConfigError(ValueError):
    pass


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"缺少环境变量 {name}")
    return value


def _load_default_fields() -> List[Dict[str, Any]]:
    raw = os.getenv("MEEGO_DEFAULT_FIELDS_JSON", "[]").strip() or "[]"
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("MEEGO_DEFAULT_FIELDS_JSON 必须是合法 JSON") from exc
    if not isinstance(value, list):
        raise ConfigError("MEEGO_DEFAULT_FIELDS_JSON 必须是 JSON 数组")
    return value


@dataclass(frozen=True)
class Settings:
    app_id: str
    app_secret: str
    meego_base_url: str
    meego_plugin_id: str
    meego_plugin_secret: str
    meego_user_key: str
    meego_project_key: str
    meego_work_item_type_key: str
    meego_template_id: int
    meego_default_fields: List[Dict[str, Any]]
    meego_description_field_key: str
    meego_item_url_template: str

    @classmethod
    def from_env(cls) -> "Settings":
        template_id_raw = _required("MEEGO_TEMPLATE_ID")
        try:
            template_id = int(template_id_raw)
        except ValueError as exc:
            raise ConfigError("MEEGO_TEMPLATE_ID 必须是整数") from exc

        return cls(
            app_id=_required("APP_ID"),
            app_secret=_required("APP_SECRET"),
            meego_base_url=os.getenv(
                "MEEGO_BASE_URL", "https://meego.larkoffice.com"
            ).rstrip("/"),
            meego_plugin_id=_required("MEEGO_PLUGIN_ID"),
            meego_plugin_secret=_required("MEEGO_PLUGIN_SECRET"),
            meego_user_key=_required("MEEGO_USER_KEY"),
            meego_project_key=_required("MEEGO_PROJECT_KEY"),
            meego_work_item_type_key=_required("MEEGO_WORK_ITEM_TYPE_KEY"),
            meego_template_id=template_id,
            meego_default_fields=_load_default_fields(),
            meego_description_field_key=os.getenv(
                "MEEGO_DESCRIPTION_FIELD_KEY", ""
            ).strip(),
            meego_item_url_template=os.getenv("MEEGO_ITEM_URL_TEMPLATE", "").strip(),
        )
