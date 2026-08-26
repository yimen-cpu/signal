# @机器人创建 Meego 工作项

这是一个基于飞书长连接的机器人示例。用户在群里 @机器人并发送创建命令后，机器人会调用 Meego（飞书项目）OpenAPI 创建工作项，并在原消息下回复结果。

## 使用效果

```text
@机器人 创建 Meego 工作项 优化登录页加载速度
补充描述：首屏加载耗时较长，请排查静态资源。
```

支持 `创建 Meego`、`创建飞书项目`，以及“表单 / 工作项 / 需求 / 缺陷”等可选关键词。第一行作为标题，后续行作为描述。

## 1. 飞书应用配置

1. 在飞书开放平台创建企业自建应用并启用机器人。
2. 为应用开通读取消息、发送/回复消息所需权限。
3. 在事件订阅中选择“使用长连接接收事件”，订阅 `im.message.receive_v1`。
4. 发布应用版本，并把机器人加入需要使用的群聊。

## 2. Meego 插件配置

1. 在 Meego 开放平台创建插件。
2. 为插件开通“读取工作项元数据”和“创建工作项”权限并发布。
3. 由目标空间管理员安装插件。
4. 获取 Plugin ID、Plugin Secret、执行人的 User Key、空间 Project Key、工作项类型和模板 ID。

程序启动时会先请求创建工作项元数据，以便尽早发现空间、类型或权限配置错误。

## 3. 配置环境变量

复制 `.env.example` 中的变量到运行环境。不要提交真实的 Secret。

必填项：

- `APP_ID`、`APP_SECRET`
- `MEEGO_PLUGIN_ID`、`MEEGO_PLUGIN_SECRET`、`MEEGO_USER_KEY`
- `MEEGO_PROJECT_KEY`、`MEEGO_WORK_ITEM_TYPE_KEY`、`MEEGO_TEMPLATE_ID`

如果模板还有其他必填字段，请按照元数据接口返回的字段格式，通过 `MEEGO_DEFAULT_FIELDS_JSON` 提供。例如：

```bash
export MEEGO_DEFAULT_FIELDS_JSON='[{"field_key":"priority","field_value":"P1"}]'
```

## 4. 启动

```bash
cd meego_bot/python
python3 -m pip install -r requirements.txt
export APP_ID='cli_xxx'
export APP_SECRET='xxx'
# 继续配置 .env.example 中其余必填变量
python3 main.py
```

## 安全说明

- 所有凭据只从环境变量读取。
- `.env` 已被仓库根目录的 `.gitignore` 忽略。
- 不要把 Plugin Secret、App Secret 或访问令牌写入代码、截图或聊天消息。
- 机器人仅在群聊中被 @ 时响应；同一进程内会对已处理消息做一小时去重，降低事件重试导致重复创建的风险。
