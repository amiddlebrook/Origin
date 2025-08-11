FROM python:3.11-slim

ARG INSTALL_PLAYWRIGHT=false
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y build-essential wget curl gnupg ca-certificates \
    && pip install --no-cache-dir -r /app/requirements.txt \
RUN if [ "${INSTALL_PLAYWRIGHT}" = "true" ] ; then \
    apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libxss1 && \
    python -m playwright install chromium ; \
fi
COPY . /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]