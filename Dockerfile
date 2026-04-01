FROM opencfd/openfoam-default:latest

USER root

# PyVistaなどの可視化で必要なライブラリ (仮想ディスプレイ用xvfb含む) をインストール
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    xvfb \
    libxcursor1 \
    libxrender1 \
    libxfixes3 \
    libxi6 \
    libxext6 \
    libx11-6 \
    libsm6 \
    libice6 \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# コンテナ側のPython仮想環境を作成
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 必要なPythonパッケージをインストール
RUN pip install --upgrade pip && \
    pip install pyvista imageio pandas numpy vtk

# 実行時ディレクトリ
WORKDIR /data
