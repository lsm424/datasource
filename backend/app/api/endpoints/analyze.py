"""资源分析对话 API：会话、历史消息、流式对话"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.schemas.analyze import SessionCreate, SessionPublic, MessagePublic, ChatRequest
from app.services import analyze_service

router = APIRouter()


def _session_to_public(s):
    return SessionPublic(
        id=s.id,
        user_id=s.user_id,
        resource_key=s.resource_key,
        resource_display_name=s.resource_display_name,
        datasource_type=s.datasource_type,
        datasource_id=s.datasource_id,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _message_to_public(m):
    return MessagePublic(
        id=m.id,
        session_id=m.session_id,
        role=m.role,
        content=m.content,
        created_at=m.created_at,
    )


@router.post("/sessions", response_model=SessionPublic)
def get_or_create_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取或创建资源分析会话（按用户+资源唯一）"""
    session = analyze_service.get_or_create_session(
        db,
        current_user.id,
        body.resource_key,
        body.resource_display_name,
        body.datasource_type,
        body.datasource_id,
    )
    return _session_to_public(session)


@router.get("/sessions/{session_id}/messages")
def list_messages(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取会话下的历史消息（不返回 system 提示词）"""
    messages = analyze_service.get_messages(db, session_id, current_user.id)
    visible = [m for m in messages if m.role != "system"]
    return {"items": [_message_to_public(m) for m in visible]}


@router.post("/sessions/{session_id}/chat")
def chat_stream(
    session_id: str,
    body: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """发送一条消息并流式返回助手回复（SSE）"""
    def generate():
        # 立即发送首条 SSE，避免大模型首 token 前连接被前端/代理判为超时
        # yield f"data: {json.dumps({'content': ''}, ensure_ascii=False)}\n\n"
        try:
            for chunk in analyze_service.chat_stream(
                db, session_id, current_user.id, body.content
            ):
                line = f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                yield line
        except GeneratorExit:
            # 客户端断开，正常退出，不当作错误
            return
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
