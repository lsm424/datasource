"""
资源分析服务：获取资源内容 + OpenAI 兼容接口流式对话
"""
import threading
import queue
import base64
import os
import json
import logging
import tempfile
import uuid
import asyncio
from datetime import datetime
from typing import Generator, Dict, Any, List, Optional
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain.agents import create_agent
from langchain.tools import tool
from sqlalchemy.orm import Session

from app.models.datasource import DataSource, DataSourceType
from app.models.resource_chat import ResourceChatSession, ResourceChatMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

from openai import OpenAI

# 优先使用 OPENAI_BASE_URL/OPENAI_MODEL，其次回退到 OLLAMA 的 /v1 代理
base_url = settings.OPENAI_BASE_URL or (settings.OLLAMA_BASE_URL.rstrip("/") + "/v1")
model = getattr(settings, "OPENAI_MODEL", None) or getattr(settings, "OLLAMA_MODEL", None)
api_key = getattr(settings, "OPENAI_API_KEY", None) or "dummy"
client = OpenAI(base_url=base_url, api_key=api_key)
logger.info(f"OpenAI 客户端初始化，模型={model}，API_KEY={api_key}, BASE_URL={base_url}")


# 图表存储配置
CHARTS_DIR = Path(settings.STATIC_FILES_DIRECTORY) / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_URL_PREFIX = "/static/charts"
    
VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm")


# ==================== 工具定义 ====================
@tool
def generate_trend_chart(csv_data: str, time_column: str, value_columns: List[str], title: Optional[str] = "数据趋势图") -> str:
    """
    根据CSV数据生成多曲线趋势图，保存为文件并返回可访问的URL。

    Args:
        csv_data: CSV格式的数据字符串，包含表头
        time_column: 时间列的列名，作为横轴
        value_columns: 数值列的列名列表，作为纵轴（支持多列）
        title: 图表标题，默认为"数据趋势图"

    Returns:
        Markdown格式的图片标签，如：![趋势图](/static/charts/trend_xxx.png)
    """
    logger.info(f"开始生成趋势图，数据长度={len(csv_data)}，时间列={time_column}，数值列={value_columns}，标题={title}")
    try:
        import pandas as pd
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端
        import matplotlib.pyplot as plt

        # 解析CSV数据
        import io
        df = pd.read_csv(io.StringIO(csv_data))

        # 检查列是否存在
        if time_column not in df.columns:
            return f"错误：时间列 '{time_column}' 不存在于数据中。可用列：{list(df.columns)}"

        missing_cols = [col for col in value_columns if col not in df.columns]
        if missing_cols:
            return f"错误：以下数值列不存在于数据中：{missing_cols}。可用列：{list(df.columns)}"

        # 创建图表
        plt.figure(figsize=(12, 6))

        # 绘制每条曲线
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
        for i, col in enumerate(value_columns):
            color = colors[i % len(colors)]
            plt.plot(df[time_column], df[col], marker='o', linewidth=2,
                    markersize=4, label=col, color=color)

        # 设置图表样式
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.xlabel(time_column, fontsize=12)
        plt.ylabel('数值', fontsize=12)
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.xticks(rotation=45)

        # 自动调整布局
        plt.tight_layout()

        # 生成文件名并保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trend_{timestamp}_{uuid.uuid4().hex[:8]}.png"
        filepath = CHARTS_DIR / filename
        plt.savefig(filepath, format='png', dpi=150, bbox_inches='tight')
        plt.close()

        # 返回Markdown格式的图片URL
        image_url = f"{CHARTS_URL_PREFIX}/{filename}"
        logger.info(f"生成趋势图成功，URL: {image_url}")
        return f"![{title}]({image_url})"

    except Exception as e:
        logger.exception("生成趋势图失败")
        return f"生成趋势图时发生错误：{str(e)}"

# CSV分析工具列表
CSV_TOOLS = [generate_trend_chart]


# ==================== LangChain LLM 服务 ====================

class LLMAnalyzeService:
    """基于 LangChain 的 LLM 分析服务，支持工具调用"""

    def __init__(self, tools=None):
        """
        初始化 LLM 分析服务
        :param tools: 工具列表，默认为空列表
        """
        self.tools = tools or []
        # 初始化 LangChain ChatOpenAI
        self.llm = ChatOpenAI(
            model=model or "gpt-4",
            base_url=base_url,
            api_key=api_key or "dummy",
            temperature=0.2,
        )
        self.agent = create_agent(
            self.llm,
            self.tools,
        )
        logger.info(f"LangChain Agent 创建成功，工具数量: {len(self.tools)}")

    def _convert_messages(self, messages: list) -> list:
        """将字典格式的消息转换为 LangChain 消息对象"""
        langchain_messages = []
        for msg in messages:
            role = msg.get('role')
            content = msg.get('content', '')
            if role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            elif role == 'user':
                langchain_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
        return langchain_messages

    def chat_stream(self, messages: list):
        """
        流式对话
        :param messages: 消息列表
        :return: 生成器，逐段返回响应内容
        """
        langchain_messages = self._convert_messages(messages)

        try:
            # 如果有工具，使用 Agent 进行流式调用
            if self.tools:
                # 使用 stream + stream_mode="messages" 实现 token 级流式输出
                for msg_chunk, metadata in self.agent.stream(
                    {"messages": langchain_messages},
                    stream_mode="messages"
                ):
                    # msg_chunk 是消息片段，包含 token 内容
                    if hasattr(msg_chunk, 'content') and msg_chunk.content:
                        yield msg_chunk.content
            else:
                # 无工具时直接使用 LLM 流式输出，实现真正的逐 token 流式
                for chunk in self.llm.stream(langchain_messages):
                    if chunk.content:
                        yield chunk.content
        except Exception as e:
            logger.exception("LangChain 流式调用失败")
            yield f"[错误: {e}]"


def _parse_config(config):
    if isinstance(config, str):
        return json.loads(config)
    if isinstance(config, dict):
        return config
    raise ValueError("无效的数据源配置")


def _extract_video_preview(path: str, need_delete: bool = False) -> Dict[str, Any]:
    """
    从本地视频文件中按配置频率抽帧，拼接成一张预览图片（base64），用于 AI 多模态分析 / 预览。
    依赖 opencv-python-headless。
    """
    try:
        import cv2  # type: ignore
        import base64
    except ImportError as e:
        raise ValueError("视频预览需要安装 opencv-python-headless 依赖") from e

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("无法打开视频文件进行预览")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    interval_sec = getattr(settings, "VIDEO_FRAME_INTERVAL_SECONDS", 2)
    max_frames = getattr(settings, "VIDEO_MAX_FRAMES", 3)
    try:
        interval_sec = int(interval_sec)
    except Exception:
        interval_sec = 5
    try:
        max_frames = int(max_frames)
    except Exception:
        max_frames = 3
    max_frames = max(1, max_frames)
    frame_interval = max(int(fps * interval_sec), 1)

    frames = []
    frame_idx = 0
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            frames.append(frame)
        elif frame_idx % 150 == 0:
            yield ''
        frame_idx += 1
    cap.release()
    
    if need_delete:
        os.remove(path)

    if not frames:
        raise ValueError("无法从视频中抽取预览帧")

    if len(frames) == 1:
        combined = frames[0]
    else:
        combined = cv2.hconcat(frames)

    ok, buf = cv2.imencode(".jpg", combined)
    if not ok:
        raise ValueError("视频预览帧编码失败")
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    yield {"type": "video", "text": "", "image_base64": b64}


def _summarize_visual_with_llm(image_b64: str, kind: str) -> str:
    """
    使用多模态大模型先对图片/视频预览做一次总结，得到纯文本描述，供后续对话作为 system 提示。
    kind: '图片资源' / '视频资源'
    """
    try:
        prompt = (
            f"下面是一份{kind}的预览图。"
            "请用中文详细、客观地描述画面中的主要内容、关键元素、布局结构以及明显的文字或标记，"
            "这一段描述将作为后续针对该资源提问时的上下文，请不要回答其他问题。"
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ],
            }
        ]
        # 使用流式接口获取描述内容
        full_chunks: List[str] = []
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and getattr(delta, "content", None):
                part = delta.content
                full_chunks.append(part)
        text = "".join(full_chunks)
        return (text or "").strip() or f"{kind}预览图，模型未给出有效描述。"
    except Exception as e:
        logger.exception("多模态预览总结失败")
        return f"{kind}预览图，但在解析时发生错误：{e}"


def _chat_with_llm(messages: list, stream=False, tools=None):
    """
    使用 LLMAnalyzeService 调用大模型（保留子线程逻辑）
    :param stream: 是否流式返回
    :param tools: 工具列表，用于 CSV 分析等场景
    """
    result_q = queue.Queue()

    def _llm():
        try:
            llm_service = LLMAnalyzeService(tools=tools or [])
            full_chunks = []
            for chunk in llm_service.chat_stream(messages):
                if chunk:
                    if stream:
                        result_q.put(chunk)
                    else:
                        full_chunks.append(chunk)
            if not stream:
                result_q.put("".join(full_chunks))
        except Exception as e:
            logger.exception("LLMAnalyzeService 调用失败")
            result_q.put(f"[错误: {e}]")
        result_q.put(True)

    threading.Thread(target=_llm, daemon=True).start()

    while True:
        try:
            r = result_q.get(timeout=3.5)
        except BaseException as e:
            r = ''

        if r == True:
            break
        if stream:
            yield r
        else:
            yield r
            break

def _get_resource_content_fs(db: Session, datasource_id: str, path: str) -> Dict[str, Any]:
    """文件系统：读取文件内容，文本 / 图片 / 视频预览"""
    ds = (
        db.query(DataSource)
        .filter(DataSource.id == datasource_id, DataSource.type == DataSourceType.FILESYSTEM)
        .first()
    )
    if not ds:
        raise ValueError("数据源不存在")
    config = _parse_config(ds.config)
    base_path = os.path.normpath(config["path"])
    rel = path.lstrip("/").replace("/", os.sep)
    full_path = os.path.normpath(os.path.join(base_path, rel))
    if not full_path.startswith(base_path):
        raise ValueError("非法路径")
    if not os.path.isfile(full_path):
        raise ValueError("文件不存在")
    ext = os.path.splitext(full_path)[1].lower()

    # 视频：抽帧生成预览图
    if ext in VIDEO_EXTS:
        return _extract_video_preview(full_path)

    # 图片：返回 base64 供多模态
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"):
        import base64

        with open(full_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return [{"type": "image", "text": "", "image_base64": b64}]

    # 文本/CSV
    if ext == ".csv":
        try:
            import pandas as pd

            df = pd.read_csv(full_path, nrows=500)
            text = f"CSV列名: {list(df.columns)}\n前500行:\n{df.head(500).to_string()}"
        except Exception:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read(50000)
        return [{"type": "csv", "text": text}]

    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read(50000)
    return [{"type": "text", "text": text}]


def _get_resource_content_os(db: Session, datasource_id: str, bucket: str, key: str) -> Dict[str, Any]:
    """对象存储：读取对象内容"""
    ds = (
        db.query(DataSource)
        .filter(DataSource.id == datasource_id, DataSource.type == DataSourceType.OBJECT_STORAGE)
        .first()
    )
    if not ds:
        raise ValueError("数据源不存在")
    from app.services.minio_service import create_minio_service_with_retry

    config = _parse_config(ds.config)
    minio_svc = create_minio_service_with_retry(config)
    response = minio_svc.download_object(bucket, key)
    try:
        data = response.read()
    finally:
        # 及时释放连接，避免连接池占用和读取状态异常
        response.close()
        response.release_conn()
    ext = os.path.splitext(key)[1].lower()
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"):
        return [{"type": "image", "text": "", "image_base64": base64.b64encode(data).decode("utf-8")}]
    if ext in VIDEO_EXTS:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=ext or ".mp4", delete=False) as tmp_file:
                tmp_file.write(data)
                tmp_file.flush()
                tmp_path = tmp_file.name
            return _extract_video_preview(tmp_path, need_delete=True)
        except Exception as e:
            logger.warning("对象存储视频抽帧失败: %s", e)
        
        return [{
            "type": "video",
            "text": "对象存储中的视频抽帧失败，仅能根据文件名和上下文做简要分析。",
        }]
    if ext == ".csv":
        try:
            import pandas as pd
            import io

            df = pd.read_csv(io.BytesIO(data), nrows=500)
            text = f"CSV列名: {list(df.columns)}\n前500行:\n{df.head(500).to_string()}"
        except Exception:
            text = data.decode("utf-8", errors="replace")[:50000]
        return [{"type": "csv", "text": text}]
    return [{"type": "text", "text": data.decode("utf-8", errors="replace")[:50000]}]


def _get_resource_content_db(db: Session, datasource_id: str, table_name: str) -> Dict[str, Any]:
    """数据库：表前 100 条转为文本"""
    ds = (
        db.query(DataSource)
        .filter(DataSource.id == datasource_id, DataSource.type == DataSourceType.DATABASE)
        .first()
    )
    if not ds:
        raise ValueError("数据源不存在")
    config = _parse_config(ds.config)
    if config.get("db_type") != "MySQL":
        raise ValueError("仅支持 MySQL")
    import pymysql

    conn = pymysql.connect(
        host=config.get("host", "localhost"),
        port=config.get("port", 3306),
        user=config.get("user", "root"),
        password=config.get("password", ""),
        database=config.get("database", ""),
        charset=config.get("charset", "utf8mb4"),
    )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(f"SELECT * FROM `{table_name}` LIMIT 100")
            rows = cur.fetchall()
        if not rows:
            text = f"表 {table_name} 暂无数据"
        else:
            import pandas as pd

            df = pd.DataFrame(rows)
            text = f"表 {table_name} 前100条:\n{df.to_string()}"
        return [{"type": "db_table", "text": text}]
    finally:
        conn.close()


def get_resource_content(db: Session, resource_key: str) -> Dict[str, Any]:
    """根据 resource_key 获取资源内容。返回 {type: 'text'|'image'|'csv'|'db_table'|'video', text: str, image_base64?: str}"""
    parts = resource_key.split(":", 2)
    if len(parts) < 3:
        raise ValueError("无效的 resource_key")
    kind, datasource_id, rest = parts[0], parts[1], parts[2]
    if kind == "filesystem":
        return _get_resource_content_fs(db, datasource_id, rest)
    if kind == "object_storage":
        sub = rest.split(":", 1)
        bucket = sub[0]
        key = sub[1] if len(sub) > 1 else ""
        return _get_resource_content_os(db, datasource_id, bucket, key)
    if kind == "database":
        return _get_resource_content_db(db, datasource_id, rest)
    raise ValueError("不支持的 datasource_type")


def get_or_create_session(
    db: Session,
    user_id: str,
    resource_key: str,
    resource_display_name: str,
    datasource_type: str,
    datasource_id: str,
) -> ResourceChatSession:
    """获取或创建会话"""
    session = (
        db.query(ResourceChatSession)
        .filter(
            ResourceChatSession.user_id == user_id,
            ResourceChatSession.resource_key == resource_key,
        )
        .first()
    )
    if session:
        return session
    session = ResourceChatSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        resource_key=resource_key,
        resource_display_name=resource_display_name,
        datasource_type=datasource_type,
        datasource_id=datasource_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_messages(db: Session, session_id: str, user_id: str) -> List[ResourceChatMessage]:
    """获取会话消息列表（校验归属）"""
    session = (
        db.query(ResourceChatSession)
        .filter(
            ResourceChatSession.id == session_id,
            ResourceChatSession.user_id == user_id,
        )
        .first()
    )
    if not session:
        return []
    return (
        db.query(ResourceChatMessage)
        .filter(ResourceChatMessage.session_id == session_id)
        .order_by(ResourceChatMessage.created_at)
        .all()
    )


def chat_stream(
    db: Session,
    session_id: str,
    user_id: str,
    user_content: str,
) -> Generator[str, None, None]:
    """
    流式对话：加载会话与资源内容，调用 OpenAI 兼容接口，保存消息并 yield 流式片段。
    """

    # 历史消息（不含本轮用户输入）
    history = get_messages(db, session_id, user_id)
    openai_messages: List[Dict[str, Any]] = []

    # 初始化 res_type，用于后续判断是否需要使用 CSV 工具
    res_type = "text"

    # 1）仅首轮注入带资源内容的 system 提示（同时写入数据库，但前端不展示）
    if len(history) == 0:
        # 获取资源内容（用于首轮 system 提示）
        session = (
            db.query(ResourceChatSession)
            .filter(
                ResourceChatSession.id == session_id,
                ResourceChatSession.user_id == user_id,
            )
            .first()
        )
        if not session:
            raise ValueError("会话不存在或无权访问")
        try:
            # 加载资源内容（图片/视频会先抽帧生成预览图），这里不再尝试通过 yield 空字符串做“心跳”，
            # 保持逻辑简单，由后续大模型流式响应阶段统一负责链路保活。
            for resource_content in get_resource_content(db, session.resource_key):
                if resource_content != "":
                    break
        except Exception as e:
            logger.warning("获取资源内容失败: %s", e)
            resource_content = {"type": "text", "text": f"（无法加载资源：{e}）"}
        res_type = resource_content.get("type", "text")
        # 对图片/视频类型，优先调用一次多模态模型将 image_base64 总结为纯文本；
        # 其它类型则直接使用已有的 text 字段。
        if res_type in ("image", "video") and resource_content.get("image_base64"):
            kind_label = "图片资源" if res_type == "image" else "视频资源"
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", "text": f"下面是一份{kind_label}的预览图。"
"请用中文详细、客观地描述画面中的主要内容、关键元素、布局结构以及明显的文字或标记，"
"这一段描述将作为后续针对该资源提问时的上下文，请不要回答其他问题。"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{resource_content['image_base64']}"},
                        },
                    ],
                }
            ]
            logger.info(f'首次解读{kind_label}: {session.resource_key}')
            for summary_text in _chat_with_llm(messages, False):
                if summary_text == '':
                    yield summary_text
            logger.info(f'解析结果：{summary_text}')
            resource_text = (summary_text or "")[:30000]
        else:
            resource_text = (resource_content.get("text") or "")[:30000]
        if res_type == "csv":
            type_desc = "CSV 表格数据文件"
            extra = (
                "请将其视为表格数据，列为字段、行为记录，可以做统计、分组、趋势对比等分析。"
                "回答时尽量引用具体列名和数值，不要捏造不存在的列或行。"
            )
            # CSV 场景添加工具说明
            extra += (
                "\n\n【可用工具】\n"
                "当用户要求生成趋势图、可视化数据、绘制图表时，请调用 generate_trend_chart 工具。\n"
                "工具参数说明：\n"
                "- csv_data: CSV数据字符串（使用上面的【资源内容】中的数据）\n"
                "- time_column: 时间列名（如 'Year'）\n"
                "- value_columns: 数值列名列表（如 ['Mean'] 或 ['5%', 'Mean', '95%']）\n"
                "- title: 图表标题\n"
                "工具会返回 Markdown 格式的图片链接，直接嵌入到回复中即可。"
            )
        elif res_type == "db_table":
            type_desc = "数据库表数据（前 100 行样本）"
            extra = (
                "这些只是样例数据，代表表结构和大致分布，请据此做结构理解、字段含义说明、简单统计和业务洞察，"
                "但避免对全集数据下结论（例如精确总量）。"
            )
        elif res_type == "text":
            type_desc = "文本文件或文档内容"
            extra = "请先概括重点，再根据用户问题做针对性的解释、比较或推理。"
        elif res_type == "video":
            type_desc = "视频资源（已从视频中抽取若干帧拼接成预览图或样本）"
            extra = "你可以结合视频画面（或预览信息）和用户的问题进行分析，描述画面中的关键元素和变化趋势。"
        elif res_type == "image":
            type_desc = "图片资源"
            extra = "你可以结合图片中的内容和用户的问题进行分析，尽量描述画面中的关键元素和细节。"
        else:
            type_desc = "相关资源内容"
            extra = "请结合下面的内容回答用户问题，必要时先解释你是如何理解这些内容的。"

        system_content = (
            f"当前资源为：{type_desc}。\n"
            f"{extra}\n\n"
            f"【资源内容】\n{resource_text}"
        )
        openai_messages.append({"role": "system", "content": system_content})

        # 首轮将 system 提示词也落库，方便后续多轮重建上下文
        system_msg = ResourceChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="system",
            content=system_content,
        )
        db.add(system_msg)
        db.commit()

    # 2）历史消息
    for m in history:
        openai_messages.append({"role": m.role, "content": m.content})

    # 发给大模型的本轮 user 消息：统一使用纯文本
    user_payload: Dict[str, Any] = {"role": "user", "content": user_content}

    openai_messages.append(user_payload)

    # 将本轮用户消息写入数据库（只保存纯文本 user_content，不保存多模态结构）
    user_msg = ResourceChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=user_content,
    )
    db.add(user_msg)
    db.commit()

    # 非首轮对话时，需要查询会话获取资源类型以判断是否使用 CSV 工具
    if len(history) > 0:
        session = (
            db.query(ResourceChatSession)
            .filter(
                ResourceChatSession.id == session_id,
                ResourceChatSession.user_id == user_id,
            )
            .first()
        )
        if session:
            try:
                for resource_content in get_resource_content(db, session.resource_key):
                    if resource_content != "":
                        res_type = resource_content.get("type", "text")
                        break
            except Exception as e:
                logger.warning("非首轮获取资源类型失败: %s", e)

    logger.info("openai_messages: %s", openai_messages)
    # 全部场景使用 LangChain Agent
    # CSV 场景使用 csv_tools，其他场景不使用工具
    tools = CSV_TOOLS if res_type == "csv" else []

    full: List[str] = []

    # 使用 _chat_with_llm 进行流式对话
    logger.info(f"使用 _chat_with_llm，模型={model}，BASE_URL={base_url}，工具数={len(tools)}")
    try:
        for chunk in _chat_with_llm(openai_messages, True, tools=tools):
            if chunk:
                full.append(chunk)
            yield chunk
    except GeneratorExit:
        raise
    except Exception as e:
        logger.exception("_chat_with_llm 调用失败")
        yield f"\n\n[错误: {e}]"
        full = [str(e)]

    # 保存助手回复
    assistant_content = "".join(full)
    logger.info(f'助手回复: {assistant_content}')
    assistant_msg = ResourceChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=assistant_content,
    )
    db.add(assistant_msg)
    db.commit()

