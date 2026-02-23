# FSAE簡易CFDシステム - 実装設計書 (Implementation Design)

本ドキュメントでは、「概念設計書 (concept_design.md)」で定義した要件を実現するための、具体的なファイル構成、スクリプトの役割、およびOpenFOAM側の詳細な実装計画を記述します。

## 1. ファイルとディレクトリの構成案

システムルートディレクトリ内は大きく「ユーザー入力用ファイル」と「システム製御用ファイル（テンプレート群）」で構成されます。

```text
📁 root_directory/          # 解析実行の起点となるフォルダ
├── 📄 run_cfd.py          # [UI・フロントエンド] ユーザーが実行するPython対話スクリプト
├── 📄 extract_results.py  # [結果出力] ログをパースしてCd, Cl等をターミナルに表示するスクリプト
├── 📄 *.stl               # ユーザーが自由に配置するSTL（body.stl, tires.stl, frame.stl等）
│
└── 📁 template/           # [バックエンド基盤] OpenFOAMケースのひな形
    ├── 📄 Allrun          # Dockerコンテナ内で走る全自動解析シェルスクリプト
    ├── 📁 0/              # 初期・境界条件 (U, p, k, omega, nut)
    ├── 📁 constant/       # 物性値、乱流モデル (transportProperties, turbulenceProperties)
    │   └── 📁 triSurface/ # 移動後のSTLデータが配置されるディレクトリ
    └── 📁 system/         # メッシュ、ソルバー設定、関数オブジェクト設定
        ├── 📄 blockMeshDict
        ├── 📄 snappyHexMeshDict
        ├── 📄 controlDict
        ├── 📄 forces      # 複数パーツの力を個別に集計する設定ファイル
        └── ...
```

## 2. 各コンポーネントの実装詳細

### 2.1. Python対話型スクリプト (`run_cfd.py`) の実装仕様
ユーザーインターフェースとなり、OpenFOAMの変数へ値を橋渡しする役割を持ちます。

- **標準入力による変数取得:**
  - 風速 $V$、タイヤ有無のフラグ、グラウンドクリアランス $Z_{clearance}$を保存。
  - カレントディレクトリの `.stl` ファイルをスキャンし、`tires.stl` 以外について「フレーム等の非空力部品か」「空力部品か」を確認し、それぞれのオフセット $(x_i, y_i, z_i)$ を入力させます。
- **設定ファイルの動的書き換え (Template Rendering):**
  - Python標準の文字列置換機能を用いて、`template/0/U` (入口速度) を書き換えます。
  - `template/system/snappyHexMeshDict` について、存在するSTLファイルのリストと分類に基づき、`geometry` および `refinementSurfaces` ブロックを動的に生成・追記します。
- **STL移動スクリプト生成:**
  - 入力されたオフセット $(x_i, y_i, z_i)$ と $Z_{clearance}$ を加算し、最終的な並行移動量を算出。
  - コンテナ内で実行される `setup_stl.sh` を生成。中身は次のような `surfaceTransformPoints` コマンド列となります。
    ```bash
    surfaceTransformPoints -translate '(x y z)' ../../body.stl constant/triSurface/body.stl
    ```
- **Dockerの起動とマウント:**
  - 以下のコマンドを `subprocess` で呼び出します。
    ```bash
    docker run --rm -v $(pwd):/data -w /data openfoam/openfoam-v2312-default ./template/Allrun
    ```

### 2.2. OpenFOAMテンプレート側の実装仕様

#### A. 空間・メッシュ定義 (`system/blockMeshDict`, `system/snappyHexMeshDict`)
- **風洞のサイズ:** 車両サイズに対して十分な空間を確保。例: 入口前方に車両長の2倍、出口後方に5倍、高さ・幅は十分大きく設定（対話機能で全体ボックスを調整可能にする拡張性も持たせる）。
- **境界パッチ:** `inlet` (入口)、`outlet` (出口)、`ground` (地面 - 滑りなし壁)、`top`, `sides` (スリップ壁)。
- **スナッピー設定:**
  - 動的に `run_cfd.py` から追記された各STLに対して、空力部品レイヤー数(例: 3〜5層)、フレームにはレイヤーなし等の差分を設けます。
  - `locationInMesh` を STLの内部に入らないような適切な空間座標に設定します。

#### B. 境界・初期条件 (`0/` ディレクトリ)
- **U (流速):** `inlet` は固定風速、$x$ 方向。`ground` は movingWall または固定壁（相対速度）。車体やタイヤ等のSTLパッチは滑りなし壁（`noSlip`）。
- **p (圧力):** `outlet` は固定値(0)、他は `zeroGradient`。
- **乱流モデル (k-omega SST):** `k`, `omega` の各パッチに対する標準的な壁関数（`kqRWallFunction`, `omegaWallFunction`）を設定。

#### C. ソルバー・力集計設定 (`system/controlDict`, `system/forces`)
- **ソルバー:** 汎用的に定常非圧縮性流体解析を行う `simpleFoam` を使用。
- **forces / forceCoeffs:**
  - `controlDict` 内の `functions` ブロックにて定義。
  - ユーザーから「空力部品」として指定された全STLを対象とした全体抗力・揚力を計算。
  - （発展）可能であれば、パーツ単位（フロントウイング、リアウイング等）の力を別々に集計するブロックを動的生成し出力へ回すよう `run_cfd.py` がスクリプトを生成します。
  - 代表面積と代表長さの設定は暫定的な固定値（対話で指定可能にするか要検討）。

### 2.3. コンテナ内自動実行スクリプト (`template/Allrun`)
解析エラーを回避しつつ自動化するための bash スクリプトです。

```bash
#!/bin/sh
. /usr/lib/openfoam/openfoam/etc/bashrc # OpenFOAM環境変数ロード

# 1. 各ファイル群を /data のルートにコピー（テンプレート環境の展開）
cp -r template/0 ./
cp -r template/system ./
cp -r template/constant ./

# 2. STLファイルの移動とアセンブリ
sh setup_stl.sh

# 3. メッシュ生成プロセス
blockMesh | tee log.blockMesh
snappyHexMesh -overwrite | tee log.snappyHexMesh

# (オプション) ここでチェックや不要セル除去の topoSet

# 4. 解析実行
simpleFoam | tee log.simpleFoam

# 5. 可視化・結果出力準備
foamToVTK | tee log.foamToVTK
python extract_results.py
```

### 2.4. 結果抽出スクリプト (`extract_results.py`)
- `postProcessing/forces/0/force.dat` （または `forceCoeffs.dat`）ファイルの末尾行を正規表現や `pandas` (なければ標準ライブラリ `csv`等) で解析します。
- 最後のイテレーションで収束した圧力抗力、粘性抗力の合計値を算出し、「Total Drag [N]: ...」のように視認性の高いUIでターミナルに出力します。

## 3. 開発フェーズ (Verification Plan)
この設計に基づく実装の検証ステップは [task.md](file:///Users/sota/.gemini/antigravity/brain/5909fbcb-8911-49b9-9e5c-f95ecffcf78a/task.md) の第6章に準じます。ダミーの単純なブロックSTLを用いたスモークテストから始め、アセンブリロジックの座標確認、そしてFSAE車両の全メッシングテストへと進めます。
