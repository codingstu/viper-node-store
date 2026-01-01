from fastapi import FastAPI, BackgroundTasks, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(__file__))

from app_fastapi import app

# 导出应用供 Vercel 使用
handler = app
