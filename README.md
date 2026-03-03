# FSAE 簡易流体解析システム (OpenFOAM + Docker)

このREADMEは、**PC初心者の方でも迷わず実行できる**ように、順番どおりに説明しています。  
まずは「やること一覧」を見て、次に「手順」を上から進めてください。

---

## 1. このツールでできること

- STLファイル（車体形状）を使って、空力解析（CFD）を実行できます。
- 難しいOpenFOAM環境はDockerコンテナ内に入っているため、**ホストPCにPythonの事前インストールは不要**です（Docker実行時）。
- 解析後に、`VTK/` と `visualization_output/` に結果が出力されます。

---

## 2. 事前に必要なもの

### 必須
- Docker Desktop（Windows/Mac）

### 推奨
- ParaView（結果を3D可視化したい場合）

> Docker Desktopは、起動して「Running」状態にしてから次へ進んでください。

---

## 3. 最短の流れ（3ステップ）

1. `models/` フォルダにSTLファイルを置く  
2. `run_windows.bat` または `./run_mac.sh` を実行する  
3. 解析完了後、`VTK/` や `visualization_output/` を確認する

---

## 4. 詳しい手順（初心者向け）

## 4-1. STLファイルを用意する

このプロジェクト直下にある `models/` フォルダへ、解析したいSTLを入れてください。

- 例: `body.stl`, `front_wing.stl`, `rear_wing.stl` など
- `tires.stl`（タイヤ）と `frame.stl`（フレーム）も、置けば自動で解析に含まれます
- 何を含めるかの質問は出ません（自動判定）

---

## 4-2. 解析を開始する

### Windows
`run_windows.bat` をダブルクリック  
（またはコマンドプロンプトで実行）

```bat
run_windows.bat
```

### Mac / Linux
ターミナルでプロジェクトフォルダに移動し、以下を実行

```bash
chmod +x run_mac.sh
./run_mac.sh
```

---

## 4-3. 実行中に聞かれる内容

実行すると、画面で以下を入力します。

1. 風速（m/s）  
   - 何も入力せずEnterでデフォルト値（20）
2. メッシュ細かさ（1/2/3）  
   - 通常は `2` 推奨
3. 各STLの位置オフセット（X/Y/Z, mm）
4. 全体のグラウンドクリアランス（mm）

---

## 4-4. 完了後の出力先

- 解析の生データ: `VTK/`
- 画像・GIF: `visualization_output/`
- ログ: `logs/`

---

## 5. ParaViewで可視化する方法

1. ParaViewを起動  
2. `File > Open` で `VTK/data_XXX/internal.vtu` を開く（例: `data_300/internal.vtu`）  
3. 左側の `Apply` を押す  
4. 上部の表示項目を `p`（圧力）または `U`（速度）に変更  
5. 断面を見たい場合は `Slice` フィルタを使う

車体表面だけ見たい場合は、`VTK/data_XXX/boundary/body.vtp` を開いてください。

---

## 6. よくある困りごと（トラブルシュート）

### Q1. 何も始まらない / Dockerエラーが出る
- Docker Desktopが起動しているか確認
- Dockerを再起動して再実行

### Q2. STLが見つからないと言われる
- `models/` フォルダに `.stl` があるか確認
- 拡張子が `.STL` などでも問題ありませんが、保存場所が正しいか確認

### Q3. 解析に時間がかかる
- 正常です（モデルサイズにより数分〜数十分）
- まずはメッシュを `1` または `2` で試すと早くなります

---

## 7. 補足（環境について）

- `run_windows.bat` / `run_mac.sh` はDockerコンテナ内で `python3 run_cfd.py` を実行します
- そのため、通常運用ではホストPC側にPythonは不要です
- ただし、ホストで直接 `python3 run_cfd.py` を打つ場合はホストPythonが必要です
