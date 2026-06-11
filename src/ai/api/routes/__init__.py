"""API 路由聚合。"""

from fastapi import APIRouter

from src.ai.api.routes.agent import router as agent_router
from src.ai.api.routes.chat import router as chat_router
from src.ai.api.routes.image import router as image_router
from src.ai.api.routes.memory import router as memory_router
from src.ai.api.routes.models import router as models_router
from src.ai.api.routes.prompts import router as prompts_router
from src.ai.api.routes.rag import router as rag_router
from src.ai.api.routes.scheduler import router as scheduler_router
from src.ai.api.routes.sessions import router as sessions_router
from src.ai.api.routes.skills import router as skills_router
from src.ai.api.routes.system import router as system_router
from src.ai.api.routes.tools import router as tools_router
from src.ai.api.routes.tts import router as tts_router

api_router = APIRouter()
api_router.include_router(chat_router, prefix="/chat", tags=["对话"])
api_router.include_router(system_router, prefix="/system", tags=["系统"])
api_router.include_router(tools_router, prefix="/tools", tags=["工具"])
api_router.include_router(rag_router, prefix="/rag", tags=["RAG"])
api_router.include_router(agent_router, prefix="/agent", tags=["Agent"])
api_router.include_router(prompts_router, prefix="/prompts", tags=["提示词"])
api_router.include_router(memory_router, prefix="/memory", tags=["记忆"])
api_router.include_router(models_router, prefix="/models", tags=["模型配置"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["会话"])
api_router.include_router(image_router, prefix="/image", tags=["图像"])
api_router.include_router(tts_router, prefix="/tts", tags=["TTS"])
api_router.include_router(scheduler_router, prefix="/scheduler", tags=["定时任务"])
api_router.include_router(skills_router, prefix="/skills", tags=["技能"])
