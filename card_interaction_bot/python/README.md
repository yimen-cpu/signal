# @机器人创建 Meego 工作项

原“告警通知”卡片示例已移除。这个目录现在保留为兼容启动入口，实际运行 `../../meego_bot/python` 中的 Meego 机器人。

## 群聊命令

```text
@机器人 创建 Meego 工作项 标题
可选的详细描述
```

机器人会创建 Meego 工作项，并在原消息下回复工作项 ID 和链接。

## 配置

请参考 [`../../meego_bot/python/.env.example`](../../meego_bot/python/.env.example) 配置环境变量。原来的 `WELCOME_CARD_ID`、`ALERT_CARD_ID`、`ALERT_RESOLVED_CARD_ID` 已不再需要。

## 启动

仍可沿用原命令：

```bash
cd card_interaction_bot/python
./bootstrap.sh
```

也可以直接运行：

```bash
cd meego_bot/python
python3 -m pip install -r requirements.txt
python3 main.py
```
