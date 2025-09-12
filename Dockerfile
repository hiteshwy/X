FROM ubuntu:22.04

# Install Python, pip, tmate, and SSH client
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-pip tmate openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY darknode_bot.py .

CMD ["python3", "darknode_bot.py"]
