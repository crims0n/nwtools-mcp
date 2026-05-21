FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY app.py main.py server.py tools.py ./

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["nwtools-mcp"]
