# astrbot_plugin_furry_maowu · 兽云祭毛毛图

基于 [兽云祭](https://cloud.foxtail.cn) API 的 AstrBot 图片插件，用于在 QQ 里发毛毛图。

## 功能

- 发送 **「随机毛毛」** → 随机来一张毛毛图（类型=毛图）。
- 发送 **「来只 名字」** → 检索该名字的毛毛图（例如：`来只 阿狸`、`来只《阿狸》`）。
- 指令 **`/毛毛帮助`** → 查看用法。

## 原理

兽云祭接口分两步：

1. `GET /api/function/random?name=&type=` —— 拿到图片元数据（`id` / `picture` 等），但不含图片地址。
2. `POST /api/function/pictures?picture=&model=` —— 拿到图片的临时 URL，再用 `event.image_result` / `chain_result` 发出。

插件用 `aiohttp` 异步请求，仅在 QQ（`aiocqhttp`）平台生效。

## 配置

插件提供 `_conf_schema.json`，可在 AstrBot WebUI 的插件配置面板修改：

- `api_base`：兽云祭 API 基础地址，默认 `https://cloud.foxtail.cn/api/function`。

> 若官方地址变更或需要走镜像，直接改这里即可，无需动代码。

## 部署

将本仓库放入 AstrBot 的 `data/plugins/astrbot_plugin_furry_maowu/` 目录，或在 WebUI 插件市场 / CLI 用 `plugin i <仓库地址>` 安装，重载插件即可。

## 说明

- 仅适配 QQ（`aiocqhttp`）。
- 命中「随机毛毛 / 来只」时会阻断事件继续传播，避免同时触发 LLM。
- 若 `pictures` 接口返回 20603（私有/未登录）等，说明该图需要登录令牌，可在 `_conf_schema.json` 基础上扩展令牌配置。
