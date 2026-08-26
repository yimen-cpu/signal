import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)

import main
from config import ConfigError, Settings
from meego_client import MeegoClient


class CommandParsingTests(unittest.TestCase):
    def test_parse_title_and_description(self):
        result = main.parse_create_command(
            "创建 Meego 工作项 优化登录页\n首屏加载时间过长"
        )
        self.assertEqual(result, ("优化登录页", "首屏加载时间过长"))

    def test_accepts_chinese_product_name(self):
        self.assertEqual(
            main.parse_create_command("创建飞书项目需求 修复搜索异常"),
            ("修复搜索异常", ""),
        )

    def test_rejects_unrelated_text(self):
        self.assertIsNone(main.parse_create_command("帮我查一下状态"))

    def test_removes_mention_placeholder(self):
        message = SimpleNamespace(
            content=json.dumps({"text": "@_user_1 创建 Meego 缺陷 登录失败"}),
            mentions=[SimpleNamespace(key="@_user_1")],
        )
        self.assertEqual(main.clean_message_text(message), "创建 Meego 缺陷 登录失败")


class SettingsTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "APP_ID": "cli_test",
            "APP_SECRET": "secret",
            "MEEGO_PLUGIN_ID": "plugin",
            "MEEGO_PLUGIN_SECRET": "plugin-secret",
            "MEEGO_USER_KEY": "user",
            "MEEGO_PROJECT_KEY": "project",
            "MEEGO_WORK_ITEM_TYPE_KEY": "story",
            "MEEGO_TEMPLATE_ID": "123",
            "MEEGO_DEFAULT_FIELDS_JSON": "[]",
        },
        clear=True,
    )
    def test_loads_required_settings(self):
        settings = Settings.from_env()
        self.assertEqual(settings.meego_template_id, 123)
        self.assertEqual(settings.meego_default_fields, [])

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_required_setting(self):
        with self.assertRaises(ConfigError):
            Settings.from_env()


class MeegoClientTests(unittest.TestCase):
    def test_create_fetches_metadata_before_write(self):
        settings = Settings(
            app_id="app",
            app_secret="secret",
            meego_base_url="https://meego.example.com",
            meego_plugin_id="plugin",
            meego_plugin_secret="plugin-secret",
            meego_user_key="user",
            meego_project_key="project",
            meego_work_item_type_key="story",
            meego_template_id=123,
            meego_default_fields=[],
            meego_description_field_key="description",
            meego_item_url_template="",
        )
        client = MeegoClient(settings)
        client.get_create_metadata = Mock(return_value=[])
        client._headers = Mock(return_value={})
        client._request_json = Mock(return_value={"data": {"id": 456}})

        result = client.create_work_item("标题", "描述")

        client.get_create_metadata.assert_called_once_with()
        payload = client._request_json.call_args.kwargs["json"]
        self.assertEqual(payload["name"], "标题")
        self.assertEqual(
            payload["field_value_pairs"],
            [{"field_key": "description", "field_value": "描述"}],
        )
        self.assertEqual(result["id"], 456)


if __name__ == "__main__":
    unittest.main()
