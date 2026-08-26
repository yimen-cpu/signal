"""兼容原卡片机器人启动路径，实际运行 Meego 工作项机器人。

原“告警通知”卡片逻辑已移除。保留这个入口是为了让已有的
card_interaction_bot/python/bootstrap.sh 启动方式无需改变。
"""

import importlib.util
import sys
from pathlib import Path


MEEGO_BOT_DIR = Path(__file__).resolve().parents[2] / "meego_bot" / "python"
MEEGO_BOT_MAIN = MEEGO_BOT_DIR / "main.py"
sys.path.insert(0, str(MEEGO_BOT_DIR))

spec = importlib.util.spec_from_file_location("meego_bot_main", MEEGO_BOT_MAIN)
if spec is None or spec.loader is None:
    raise RuntimeError(f"无法加载 Meego 机器人入口：{MEEGO_BOT_MAIN}")
meego_bot_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(meego_bot_main)


if __name__ == "__main__":
    meego_bot_main.main()
