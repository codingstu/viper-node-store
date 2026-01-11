#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel Serverless Function 入口
将 backend/main.py 的 FastAPI 应用导出给 Vercel
"""

from backend.main import app

# Vercel 需要导出 app 对象
# 这是 serverless function 的入口点