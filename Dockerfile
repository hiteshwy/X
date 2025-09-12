FROM ubuntu:22.04

# Install basics
RUN apt-get update &&     apt-get install -y python3 python3-pip tmate openssh-client docker.io &&     rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY darknode_bot.py .

CMD ["python3", "darknode_bot.py"]
