FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent/ ./agent/
COPY policy_engine/ ./policy_engine/
COPY custom_mcp_server/ ./custom_mcp_server/
COPY research_mcp_server/ ./research_mcp_server/
COPY mcp_servers.json .
WORKDIR /app/agent
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
