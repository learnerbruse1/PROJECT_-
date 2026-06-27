# 后端镜像（默认文件后端，无需数据库）
FROM python:3.12-slim

WORKDIR /app

# 先装依赖以利用层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# 数据通过 compose 只读挂载到 /data
ENV DATA_BACKEND=geojson \
    DATA_DIR=/data \
    CORS_ORIGINS=*

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
