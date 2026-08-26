import json
import os
import re
import threading
import time
from typing import Any, Optional, Tuple

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
    ReplyMessageResponse,
)

from config import ConfigError, Settings
from meego_client import MeegoClient, MeegoError


COMMAND_PATTERN = re.compile(
    r"^创建\s*(?:meego|飞书项目)(?:\s*(?:表单|工作项|需求|缺陷))?\s*[：:]?\s*(.*)$",
    re.IGNORECASE | re.DOTALL,
)
HELP_TEXT = (
    "请按下面的格式发送：\n"
    "@机器人 创建 Meego 工作项 标题\n\n"
    "也可以另起一行补充描述：\n"
    "@机器人 创建 Meego 工作项 标题\n详细描述"
)

_settings: Optional[Settings] = None
_meego_client: Optional[MeegoClient] = None
_processed_messages = {}
_processing_messages = set()
_message_lock = threading.Lock()


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def get_meego_client() -> MeegoClient:
    global _meego_client
    if _meego_client is None:
        _meego_client = MeegoClient(get_settings())
    return _meego_client


def _mention_key(mention: Any) -> str:
    if isinstance(mention, dict):
        return str(mention.get("key") or "")
    return str(getattr(mention, "key", "") or "")


def clean_message_text(message: Any) -> str:
    content = json.loads(message.content or "{}")
    text = str(content.get("text") or "")
    for mention in message.mentions or []:
        key = _mention_key(mention)
        if key:
            text = text.replace(key, " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_create_command(text: str) -> Optional[Tuple[str, str]]:
    match = COMMAND_PATTERN.match(text.strip())
    if not match:
        return None

    body = match.group(1).strip()
    if not body:
        return "", ""
    lines = [line.strip() for line in body.splitlines()]
    title = lines[0]
    description = "\n".join(line for line in lines[1:] if line)
    return title, description


def reply_text(message_id: str, text: str) -> None:
    request = (
        ReplyMessageRequest.builder()
        .message_id(message_id)
        .request_body(
            ReplyMessageRequestBody.builder()
            .content(json.dumps({"text": text}, ensure_ascii=False))
            .msg_type("text")
            .build()
        )
        .build()
    )
    response: ReplyMessageResponse = lark_client.im.v1.message.reply(request)
    if not response.success():
        raise RuntimeError(
            "回复飞书消息失败，"
            f"code={response.code}, msg={response.msg}, log_id={response.get_log_id()}"
        )


def _try_reserve(message_id: str) -> bool:
    now = time.time()
    with _message_lock:
        expired = [key for key, value in _processed_messages.items() if now - value > 3600]
        for key in expired:
            del _processed_messages[key]
        if message_id in _processing_messages or message_id in _processed_messages:
            return False
        _processing_messages.add(message_id)
        return True


def _finish(message_id: str, succeeded: bool) -> None:
    with _message_lock:
        _processing_messages.discard(message_id)
        if succeeded:
            _processed_messages[message_id] = time.time()


def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
    message = data.event.message
    message_id = message.message_id

    if message.message_type != "text":
        reply_text(message_id, "暂时只支持文本消息。\n\n" + HELP_TEXT)
        return

    if message.chat_type == "group" and not message.mentions:
        return

    try:
        command = parse_create_command(clean_message_text(message))
    except (ValueError, TypeError, json.JSONDecodeError):
        reply_text(message_id, "消息解析失败，请发送纯文本。\n\n" + HELP_TEXT)
        return

    if command is None:
        reply_text(message_id, HELP_TEXT)
        return

    title, description = command
    if not title:
        reply_text(message_id, "还缺少工作项标题。\n\n" + HELP_TEXT)
        return
    if len(title) > 200:
        reply_text(message_id, "标题不能超过 200 个字符，请精简后重试。")
        return
    if not _try_reserve(message_id):
        return

    succeeded = False
    try:
        work_item = get_meego_client().create_work_item(title, description)
        item_id = work_item.get("work_item_id") or work_item.get("id")
        item_url = get_meego_client().work_item_url(work_item)
        result = f"✅ Meego 工作项创建成功\n标题：{title}"
        if item_id:
            result += f"\nID：{item_id}"
        if item_url:
            result += f"\n链接：{item_url}"
        reply_text(message_id, result)
        succeeded = True
    except (ConfigError, MeegoError) as exc:
        print(f"create Meego work item failed: {exc}")
        reply_text(message_id, f"❌ 创建失败：{exc}")
    except Exception as exc:
        print(f"unexpected error while creating Meego work item: {exc}")
        reply_text(message_id, "❌ 创建失败，请联系机器人管理员查看运行日志。")
    finally:
        _finish(message_id, succeeded)


event_handler = (
    lark.EventDispatcherHandler.builder("", "")
    .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
    .build()
)

lark_client = (
    lark.Client.builder()
    .app_id(os.getenv("APP_ID", ""))
    .app_secret(os.getenv("APP_SECRET", ""))
    .build()
)


def main() -> None:
    settings = get_settings()
    # Validate Meego project/type/permission before accepting write requests.
    get_meego_client().get_create_metadata()
    print(
        "Starting Meego bot for "
        f"project={settings.meego_project_key}, "
        f"type={settings.meego_work_item_type_key}"
    )
    ws_client = lark.ws.Client(
        settings.app_id,
        settings.app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
    )
    ws_client.start()


if __name__ == "__main__":
    main()
