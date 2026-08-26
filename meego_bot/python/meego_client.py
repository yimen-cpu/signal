import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from config import Settings


class MeegoError(RuntimeError):
    pass


class MeegoClient:
    """Minimal Meego OpenAPI client with plugin-token caching."""

    def __init__(self, settings: Settings, timeout: int = 15) -> None:
        self.settings = settings
        self.timeout = timeout
        self._token = ""
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()
        self._metadata: Optional[List[Dict[str, Any]]] = None

    def _request_json(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            response = requests.request(
                method,
                f"{self.settings.meego_base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise MeegoError(f"Meego 请求失败：{exc}") from exc
        except ValueError as exc:
            raise MeegoError("Meego 返回了无法解析的响应") from exc

        error = payload.get("error")
        if isinstance(error, dict) and error.get("code") not in (None, 0):
            raise MeegoError(error.get("msg") or error.get("display_msg") or "Meego 接口失败")
        return payload

    def _plugin_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token

        with self._token_lock:
            if self._token and time.time() < self._token_expires_at:
                return self._token
            payload = self._request_json(
                "POST",
                "/open_api/authen/plugin_token",
                headers={"Content-Type": "application/json"},
                json={
                    "plugin_id": self.settings.meego_plugin_id,
                    "plugin_secret": self.settings.meego_plugin_secret,
                    "type": 0,
                },
            )
            data = payload.get("data") or {}
            token = data.get("token")
            if not token:
                raise MeegoError("Meego 鉴权成功，但响应中没有 token")
            expires_in = int(data.get("expire_time") or 7200)
            self._token = str(token)
            self._token_expires_at = time.time() + max(expires_in - 60, 60)
            return self._token

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self._plugin_token(),
            "X-USER-KEY": self.settings.meego_user_key,
        }

    def get_create_metadata(self) -> List[Dict[str, Any]]:
        if self._metadata is not None:
            return self._metadata
        project_key = quote(self.settings.meego_project_key, safe="")
        item_type = quote(self.settings.meego_work_item_type_key, safe="")
        payload = self._request_json(
            "GET",
            f"/open_api/{project_key}/work_item/{item_type}/meta",
            headers=self._headers(),
        )
        data = payload.get("data") or []
        if isinstance(data, dict):
            data = data.get("fields") or data.get("field_list") or []
        if not isinstance(data, list):
            raise MeegoError("Meego 元数据响应格式不符合预期")
        self._metadata = data
        return data

    def create_work_item(
        self, name: str, description: str = ""
    ) -> Dict[str, Any]:
        # Creation metadata is fetched first so invalid project/type/permissions fail
        # before any write request is sent.
        self.get_create_metadata()

        fields = list(self.settings.meego_default_fields)
        if description and self.settings.meego_description_field_key:
            fields.append(
                {
                    "field_key": self.settings.meego_description_field_key,
                    "field_value": description,
                }
            )

        project_key = quote(self.settings.meego_project_key, safe="")
        payload = self._request_json(
            "POST",
            f"/open_api/{project_key}/work_item/create",
            headers=self._headers(),
            json={
                "work_item_type_key": self.settings.meego_work_item_type_key,
                "name": name,
                "template_id": self.settings.meego_template_id,
                "field_value_pairs": fields,
            },
        )
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        if data is not None:
            return {"work_item_id": data}
        raise MeegoError("Meego 未返回已创建的工作项信息")

    def work_item_url(self, work_item: Dict[str, Any]) -> str:
        for key in ("url", "work_item_url", "detail_url"):
            if work_item.get(key):
                return str(work_item[key])

        item_id = work_item.get("work_item_id") or work_item.get("id")
        if item_id and self.settings.meego_item_url_template:
            return self.settings.meego_item_url_template.format(
                project_key=self.settings.meego_project_key,
                work_item_type_key=self.settings.meego_work_item_type_key,
                work_item_id=item_id,
            )
        return ""
