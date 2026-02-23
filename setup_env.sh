#!/bin/bash

echo "=================================================="
echo "    FSAE CFD System - Environment Setup"
echo "=================================================="

# Mac環境などでdocker-credential-desktopが見つからないエラーを防ぐためパスを追加
export PATH=$PATH:/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin

# 1. Check if Docker is installed
if ! command -v docker &> /dev/null
then
    echo "エラー: Dockerがインストールされていません。"
    echo "Docker Desktopをインストールして起動してから再度実行してください。"
    echo "Mac/Windows: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# 2. Check if Docker daemon is running
if ! docker info &> /dev/null
then
    echo "エラー: Dockerが起動していません。Docker Desktopアプリケーションを開いてから再度実行してください。"
    exit 1
fi

# 3. Pull the specified OpenFOAM image
echo ""
echo "[1/3] 必要なDockerイメージ (OpenFOAM) をダウンロード（pull）しています..."
echo "      ※ イメージサイズが大きいため、初回は環境によって数分〜十数分かかります。"
docker pull opencfd/openfoam-default

if [ $? -ne 0 ]; then
    echo "エラー: Dockerイメージの取得に失敗しました。"
    echo "ネットワーク接続を確認するか、Dockerが正常に動作しているか確認してください。"
    exit 1
fi

echo ""
echo "[2/3] Python仮想環境の構築と必要なライブラリのインストールを行っています..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install pyvista imageio pandas numpy

echo ""
echo "[3/3] ディレクトリ構成の作成と権限設定を行っています..."
chmod +x template/Allrun
chmod +x extract_results.py

mkdir -p models logs
mv *.stl models/ 2>/dev/null

echo "モデル配置用フォルダ (models/) とログ保存用フォルダ (logs/) を作成しました。"

echo ""
echo "=================================================="
echo "    初期セットアップが完了しました！"
echo "    解析を行いたい設計STLファイルを models/ フォルダに置いてから、"
echo "    以下のコマンドで仮想環境を有効化し、解析を開始してください："
echo ""
echo "    source venv/bin/activate"
echo "    python3 run_cfd.py"
echo "=================================================="
