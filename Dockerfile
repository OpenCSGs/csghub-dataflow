FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.10.14
# FROM python:3.10.14
# prepare the java env
WORKDIR /opt
# download jdk
RUN wget https://aka.ms/download-jdk/microsoft-jdk-17.0.9-linux-x64.tar.gz -O jdk.tar.gz && \
    tar -xzf jdk.tar.gz && \
    rm -rf jdk.tar.gz && \
    mv jdk-17.0.9+8 jdk

# set the environment variable
ENV JAVA_HOME=/opt/jdk

WORKDIR /dataflow


RUN echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list

# install 3rd-party system dependencies
# RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  libpq-dev -y
RUN apt-get update && apt-get install libpq-dev libgl1-mesa-glx -y
RUN apt install git-lfs && git lfs install && apt clean && rm -rf /var/lib/apt/lists/*

# install data-flow then
COPY . .

ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_EXTRA_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# Install deps
# RUN pip install --no-cache-dir --use-deprecated=legacy-resolver -r docker/dataflow_requirements.txt
RUN pip install --no-cache-dir -r docker/dataflow_requirements.txt

# compile code
# RUN python -m compileall .
# RUN find ./ -name "*.py" -delete

# 下载playwright, SmartScraperGraph工具需要
#ENV PLAYWRIGHT_DOWNLOAD_HOST=https://storage.aliyun.com/playwright
#RUN playwright install --with-deps

RUN git config --global user.email "dataflow@opencsg.com"
RUN git config --global user.name "dataflow"
RUN git config --global --add safe.directory '*'

# Start fastapi API Server
EXPOSE 8000

