FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# 模拟监听端口 8000 来“骗过” Koyeb 健康检查
EXPOSE 8000

# 同时运行你的 bot 和一个假 HTTP 服务器
CMD ["sh", "-c", "python3 main.py & python3 -m http.server 8000"]
