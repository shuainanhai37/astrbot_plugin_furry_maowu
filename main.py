import re
from urllib.parse import urljoin

import aiohttp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp

# 兽云祭 API 默认地址（可在 WebUI 插件配置里修改）
DEFAULT_API_BASE = "https://cloud.foxtail.cn/api/function"
# 图片类型：0=全局 1=毛图 2=插画。毛毛插件默认只取毛图。
MAO_TYPE = "1"


class MaoWuPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config or {}
        self.api_base = (self.config.get("api_base") or DEFAULT_API_BASE).rstrip("/")
        logger.info(f"[毛毛图] API base = {self.api_base}")

    # ------------------------- 内部请求 -------------------------
    async def _random(self, name=None):
        """调用 /function/random 获取一张图片的元数据。"""
        params = {"type": MAO_TYPE}
        if name:
            params["name"] = name
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base}/random",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    data = await resp.json(content_type=None)
        except Exception as e:
            logger.error(f"[毛毛图] random 请求失败: {e}")
            return None, f"网络错误：{e}"

        pic = data.get("picture")
        if not pic:
            return None, data.get("msg") or "没有找到对应的毛毛~"
        return pic, None

    async def _fetch_url(self, picture, model):
        """调用 /function/pictures 拿到图片的临时 URL。"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/pictures",
                    params={"picture": picture, "model": model},
                    data={"token": "", "token_user": "", "token_key": ""},
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    data = await resp.json(content_type=None)
        except Exception as e:
            logger.error(f"[毛毛图] pictures 请求失败: {e}")
            return None, f"网络错误：{e}"

        url = data.get("url")
        if not url:
            return None, data.get("msg") or "未返回图片地址"
        if not url.startswith("http"):
            url = urljoin("https://cloud.foxtail.cn", url)
        return url, None

    async def _resolve_url(self, pic):
        """
        拿图片地址。random 返回的元数据里既有 SID(id) 也有 UID(picture)，
        而 pictures 接口的 model 参数含义文档未明确，这里两种都试一次，提高成功率。
        """
        sid = pic.get("id")
        uid = pic.get("picture")
        last_err = None
        for pid, model in ((sid, "0"), (uid, "1")):
            if not pid:
                continue
            url, err = await self._fetch_url(pid, model)
            if url:
                return url, None
            last_err = err
        return None, last_err or "未返回图片地址"

    async def _send_pic(self, event: AstrMessageEvent, name=None):
        """统一的取图+发图流程。"""
        pic, err = await self._random(name)
        if err:
            yield event.plain_result(f"哎呀，获取毛毛失败了：{err}")
            event.stop_event()
            return

        url, err = await self._resolve_url(pic)
        if err or not url:
            yield event.plain_result(f"拿到毛毛信息，但下载图片失败：{err or '无地址'}")
            event.stop_event()
            return

        caption = f"「{pic.get('name') or '毛毛'}」"
        if pic.get("account"):
            caption += f"  by {pic.get('account')}"
        chain = [Comp.Plain(caption), Comp.Image.fromURL(url)]
        yield event.chain_result(chain)
        event.stop_event()

    # ------------------------- 指令 -------------------------
    @filter.command("毛毛帮助")
    async def help_cmd(self, event: AstrMessageEvent):
        """查看毛毛图插件用法"""
        yield event.plain_result(
            "毛毛图插件用法：\n"
            "· 发送「随机毛毛」→ 来一张随机毛毛图\n"
            "· 发送「来只 名字」→ 检索该名字的毛毛图（如：来只 阿狸）\n"
            "仅支持 QQ 平台。"
        )

    # ------------------------- 自然语言触发（仅 QQ） -------------------------
    @filter.event_message_type(filter.EventMessageType.ALL)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def on_message(self, event: AstrMessageEvent):
        text = (event.message_str or "").strip()

        name = None
        if re.search(r"随机\s*毛毛", text):
            name = None
        else:
            m = re.match(r"来只\s*(.+)", text)
            if not m:
                return  # 不是本插件指令，交给其它处理器（如 LLM）
            name = m.group(1).strip().strip("《》「」“”\"'｜|").strip()
            if not name:
                yield event.plain_result("来只 后面要跟名字哦，例如：来只 阿狸")
                event.stop_event()
                return

        async for r in self._send_pic(event, name):
            yield r
