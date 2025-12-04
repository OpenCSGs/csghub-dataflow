ARG PYTHON_IMAGE=docker.io/python:3.10.14
FROM ${PYTHON_IMAGE}

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

# install 3rd-party system dependencies
# RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  libpq-dev -y
ARG BUILD_CN=false
RUN if [ "$BUILD_CN" = "true" ]; then \
      rm -rf /etc/apt/sources.list.d/debian.sources || true; \
      echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free" > /etc/apt/sources.list; \
      echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list; \
      echo "deb http://mirrors.aliyun.com/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list; \
    fi && \
    apt-get update && \
    apt-get install --no-install-recommends -y \
      libpq-dev \
      libgl1-mesa-glx \
      git-lfs && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    git lfs install

# install data-flow then
COPY . .

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/
# Install deps
RUN if [ "$BUILD_CN" = "true" ]; then \
      pip install --no-cache-dir -r docker/dataflow_requirements.txt -i ${PIP_INDEX_URL}; \
    else \
      pip install --no-cache-dir -r docker/dataflow_requirements.txt; \
    fi

# compile code
# RUN python -m compileall .
# RUN find ./ -name "*.py" -delete

# 下载playwright, SmartScraperGraph工具需要
#ENV PLAYWRIGHT_DOWNLOAD_HOST=https://storage.aliyun.com/playwright
#RUN playwright install --with-deps

RUN git config --global user.email "dataflow@opencsg.com" && \
    git config --global user.name "dataflow" && \
    git config --global --add safe.directory '*'

# Download required resources for offline deployment
# Create default cache directories
RUN mkdir -p /root/.cache/data_engine/assets && \
    mkdir -p /root/.cache/data_engine/models

# Download JSON resources (flagged_words and stopwords)
RUN wget -O /root/.cache/data_engine/assets/flagged_words.json \
    https://dail-wlcb.oss-cn-wulanchabu.aliyuncs.com/data_juicer/flagged_words.json && \
    wget -O /root/.cache/data_engine/assets/stopwords.json \
    https://dail-wlcb.oss-cn-wulanchabu.aliyuncs.com/data_juicer/stopwords.json

# Download SentencePiece models (Chinese and English)
RUN wget -O /root/.cache/data_engine/models/zh.sp.model \
    https://dail-wlcb.oss-cn-wulanchabu.aliyuncs.com/data_juicer/models/zh.sp.model && \
    wget -O /root/.cache/data_engine/models/en.sp.model \
    https://dail-wlcb.oss-cn-wulanchabu.aliyuncs.com/data_juicer/models/en.sp.model

# Verify downloaded files
RUN ls -lh /root/.cache/data_engine/assets/ && \
    ls -lh /root/.cache/data_engine/models/

# Start fastapi API Server
EXPOSE 8000
