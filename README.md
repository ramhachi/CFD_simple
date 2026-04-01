# FSAE 簡易流体解析システム (OpenFOAM + Docker)

このツールは、`model/` または `models/` に STL を置くだけで、OpenFOAM を使った簡易空力解析を実行できるようにしたものです。

難しい OpenFOAM 設定は自動生成されるので、基本的には「STL を入れる → 起動する → 数値を入れる」で使えます。

## 1. このツールでできること

- 任意の STL を `model/` または `models/` に入れて CFD を実行できます。
- STL のファイル名が日本語や記号を含んでいても、OpenFOAM 用の安全な名前へ自動変換します。
- STL の大きさが学生フォーミュラ相当でも、ミニ四駆相当でも、モデル寸法に合わせて風洞サイズと背景メッシュを自動調整します。
- メッシュの三段階設定 `1 / 2 / 3` はそのまま使えます。
- 解析後は `VTK/` と `logs/` に結果が出ます。

## 2. 事前に必要なもの

### 必須

- Docker Desktop

### 推奨

- ParaView

Docker Desktop は起動して `Running` 状態にしてから使ってください。

## 3. 最短の流れ

1. `model/` または `models/` フォルダに STL を入れる
2. `run_windows.bat` または `./run_mac.sh` を実行する
3. 画面の質問に答える
4. `logs/`, `VTK/`, 必要に応じて `visualization_output/` を確認する

## 4. STL の入れ方

解析対象の STL は、プロジェクト直下の次のどちらかに置いてください。

- `model/`
- `models/`

両方ある場合は、**STL が入っている方を優先**します。

### ファイル名について

- どんなファイル名でも基本的に読み込めます
- OpenFOAM 内部では自動で安全な英数字名に変換されます
- 元の STL 名に空白や記号が含まれていても、解析前に安全な一時コピーへ置き換えてから OpenFOAM に渡します
- `tires.stl` はタイヤ扱い、`frame.stl` はフレーム扱いです
- それ以外は空力対象サーフェスとして扱います

解析対象のフォルダを明示したい場合は、次のように `--stl-dir` を使ってください。

```bash
python3 run_cfd.py --stl-dir model
python3 run_cfd.py --stl-dir models
```

## 5. 実行中に聞かれる内容

実行すると、次の内容を順番に入力します。

1. 風速 `m/s`
2. メッシュ細かさ
   - `1`: 粗い
   - `2`: 普通
   - `3`: 細かい
3. 最低地上高 `mm`
    - 最も低い点と地面の距離です
    - STL 自体の原点位置がずれていても、自動で全体を持ち上げて合わせます
    - `0 mm` を指定したときは、地面と完全一致してメッシュ生成が不安定になるのを避けるため、必要時のみごく小さく自動浮上します
4. 各 STL の追加オフセット `X/Y/Z mm`

## 6. サイズ自動調整について

このシステムでは、STL の bounding box を読んで次を自動決定します。

- 風洞の前後左右上下サイズ
- `blockMesh` のセル数
- `snappyHexMesh` の内部点
- `forceCoeffs` の代表長さ `Lref`
- `forceCoeffs` の代表面積 `Aref`
- 乱流初期値の代表スケール

### 単位の自動判定

- STL 寸法の代表長さが `10` より大きい場合は `mm` とみなします
- それ以下なら `m` とみなします

つまり、たとえば次のように動きます。

- `1.6 m` の車両モデル → `m` 扱い
- `160 mm` の小型モデル → `mm` 扱い

必要ならコマンドラインで明示指定もできます。

```bash
python3 run_cfd.py --stl-unit mm
python3 run_cfd.py --stl-unit m
```

## 7. 起動方法

### Windows

```bat
run_windows.bat
```

### Mac / Linux

```bash
chmod +x run_mac.sh
./run_mac.sh
```

### Python から直接起動する場合

```bash
python3 run_cfd.py
```

この場合でも、`fsae-cfd` イメージがなければ自動で Docker ビルドを試みます。

### STL ディレクトリを明示したい場合

```bash
python3 run_cfd.py --stl-dir ./my_stls
```

## 8. 出力先

- OpenFOAM の中間・最終ログ: `logs/`
- 可視化用データ: `VTK/`
- 静止画・GIF: `visualization_output/`（生成できた場合）

## 9. ParaView で結果を見る方法（初心者向け）

この章は、**「ParaView を開いたことがない人でも、まず結果を見られること」**を目的に書いています。

最初は難しく感じますが、やることは次の 3 つです。

1. 正しいファイルを開く
2. `Apply` を押す
3. `Color By` で見たい量を選ぶ

### 9-1. まず覚えておくと楽になること

- **ファイルを開いた直後は、たいてい `Apply` を押さないと表示されません**
- フィルタ（`Slice`, `Stream Tracer` など）を追加したあとも、**毎回 `Apply` が必要**です
- 左上の **Pipeline Browser** で、今どのデータやフィルタを選んでいるか確認できます
- 何も見えなくなったら、まず **`Reset Camera`** を試してください
- 色が全部同じに見えるときは、**`Rescale to Data Range`** または **`Rescale to Visible Range`** を押してください
- STL の名前に日本語や空白があっても、ParaView 側では **OpenFOAM 用の安全名**で出ます

たとえば実行時にターミナルへ

```text
OpenFOAM名 : Part_Studio_1_Part_1.stl
```

と出ていた場合、ParaView ではこの名前を使って

```text
VTK/data_300/boundary/Part_Studio_1_Part_1.vtp
```

のようなファイルとして出力されます。

### 9-2. どのファイルを開けばよいか

このリポジトリでは、主に次のファイルを使います。

- `VTK/data.vtm.series`
  - 解析途中から最終結果までの**時系列全体**を見るときに使います
- `VTK/data_300.vtm`
  - 最終ステップだけを**まとめて**見るときに使います
- `VTK/data_300/internal.vtu`
  - 流体内部の速度や圧力を見たいときに使います
- `VTK/data_300/boundary/<OpenFOAM名>.vtp`
  - 車体表面だけを見たいときに使います
- `VTK/data_300/boundary.vtm`
  - 車体・地面・入口・出口などの境界面をまとめて見たいときに使います

**最初のおすすめ**は次の 2 つです。

- 流れ全体を見る: `VTK/data.vtm.series`
- 車体表面の圧力を見る: `VTK/data_300/boundary/<OpenFOAM名>.vtp`

### 9-3. ParaView を開いた直後の最短手順

1. ParaView を起動します
2. `File` → `Open` から `VTK/data.vtm.series` を選びます
3. 左側の `Properties` で **`Apply`** を押します
4. 上側の時間コントロールで、いちばん右の時刻（普通は `300`）へ移動します
5. 表示上部の `Color By` で `U` を選び、右側の成分を **`Magnitude`** にします
6. `Reset Camera` を押して全体を表示します

これだけで、まず「どこが速く、どこが遅いか」が見えます。

### 9-4. 車体表面の圧力を見る手順

これは初心者の方には **いちばん簡単な確認方法**です。

#### 手順

1. `File` → `Open` で `VTK/data_300/boundary/<OpenFOAM名>.vtp` を開きます
2. `Apply` を押します
3. `Color By` で **`p`** を選びます
4. 色バー横の **`Rescale to Data Range`** を押します
5. 表示方法を `Surface` にします
6. 形を見やすくしたいときは `Surface With Edges` に変えます
7. 色バーを表示したいときは、`Show Color Legend` をオンにします

#### 見るポイント

- 車体前面で圧力が高くなっていれば、よどみ点の傾向が見えています
- 車体上面や後流側で圧力が低くなっていれば、加速や剥離の傾向が見えます
- 全部同じ色に見えるときは、`p` 以外を選んでいないか、色スケールが更新されていない可能性があります

#### うまく見えないとき

- 何も出ない → `Apply`
- 小さすぎて見えない → `Reset Camera`
- 色が変わらない → `Rescale to Data Range`

### 9-5. 断面（スライス）で速度や圧力を見る手順

断面図は、**後流の広がり**や**床近くの流れ**を見るのに便利です。

#### 手順

1. `File` → `Open` で `VTK/data_300/internal.vtu` を開きます
2. `Apply` を押します
3. そのデータを選んだ状態で `Filters` → `Slice` を追加します
4. `Apply` を押します
5. `Color By` で見たい量を選びます
   - 速度を見たい → `U` の `Magnitude`
   - 圧力を見たい → `p`
6. スライス平面をドラッグして見たい位置へ動かします

#### どの向きで切ればよいか

- `Normal = Y`  
  車体中心を通る**縦断面**になりやすく、前後の流れや後流が見やすいです
- `Normal = X`  
  車体前後のある位置での**断面分布**を見たいときに使います
- `Normal = Z`  
  地面近くや上面付近の**平面分布**を見るのに向いています

#### 見るポイント

- 車体後ろに低速域が伸びていれば、後流が大きい可能性があります
- 床と車体の間で流速が上がっていれば、その隙間で流れが加速しています
- 圧力で見ると、前方高圧・上面や後流側低圧の傾向が追いやすいです

### 9-6. 流線（Stream Tracer）を見る手順

流線は、**流れがどちらへ曲がるか**、**どこで剥がれそうか**を見るのに便利です。

#### 手順

1. `File` → `Open` で `VTK/data_300/internal.vtu` を開きます
2. `Apply` を押します
3. そのデータを選んだ状態で `Filters` → `Alphabetical` → `Stream Tracer` を選びます
4. `Vectors` を **`U`** にします
5. `Seed Type` は最初は **`Line`** がおすすめです
6. 3D ビュー上の seed（線）を、**車体の少し前**に置きます
7. seed が車体内部や地面内部に入らないように調整します
8. `Apply` を押します
9. `Color By` を `U` の `Magnitude` にします
10. 線が細くて見えにくいときは、さらに `Filters` → `Tube` を追加します

#### seed の置き方のコツ

- 車体の真正面より**少し上流側**に置く
- 車体を貫通しないようにする
- まずは短い線で少数の流線を出し、見えてから増やす

#### 見るポイント

- 流線が車体に沿って滑らかに流れるか
- 車体後方で急に広がったり、巻いたりしていないか
- 地面近くで流れが強く曲がっていないか

#### 流線が出ないとき

- `Vectors` が `U` になっていない
- seed が流体領域の外にある
- seed が車体内部に入っている
- `Apply` を押していない

### 9-7. 時系列で変化を見る手順

このリポジトリでは `VTK/data.vtm.series` に、`0, 20, 40, ... 300` の時刻がまとまっています。

#### 手順

1. `VTK/data.vtm.series` を開いて `Apply`
2. 上側の再生ボタンで時間を進める
3. 右端の時刻へ飛べば、最終状態を確認できます
4. `File` → `Save Animation` で動画として保存できます

最初は**最終時刻だけ見る**方が分かりやすいです。慣れてきたら、途中から最終へどう変わるかを見ると理解しやすくなります。

### 9-8. 初心者向けのおすすめ確認順

迷ったら、次の順で見ると理解しやすいです。

1. `VTK/data_300/boundary/<OpenFOAM名>.vtp` で車体表面の `p`
2. `VTK/data_300/internal.vtu` で `Slice` を使い、`U` の `Magnitude`
3. 同じ `internal.vtu` で `Stream Tracer`
4. 慣れてきたら `VTK/data.vtm.series` で時間変化

### 9-9. ParaView 公式ドキュメント

この README だけでも最低限は操作できますが、より詳しく知りたいときは **ParaView 公式ドキュメント** を必ず参照してください。

- 公式トップ: <https://docs.paraview.org/en/latest/>
- User's Guide: <https://docs.paraview.org/en/latest/UsersGuide/index.html>
- データの開き方: <https://docs.paraview.org/en/latest/UsersGuide/dataIngestion.html>
- 表示の基本: <https://docs.paraview.org/en/latest/UsersGuide/displayingData.html>
- フィルタの使い方: <https://docs.paraview.org/en/latest/UsersGuide/filteringData.html>
- アニメーション: <https://docs.paraview.org/en/latest/UsersGuide/animation.html>
- 初心者向けチュートリアル: <https://docs.paraview.org/en/latest/Tutorials/ClassroomTutorials/beginningParaView.html>

ParaView はバージョンによって、ボタン名や表示位置が少し変わることがあります。その場合も、基本は **`Open` → `Apply` → `Color By` → `Filter`** の流れです。

## 10. 物理量の見方

ターミナルには主に次が表示されます。

- `Cd`: 抗力係数
- `Cl`: 揚力係数
- `Cs`: 横力係数
- `Total Drag [N]`: 抗力
- `Total Lift [N]`: 揚力
- `Reference Length / Area`: 係数計算に使った代表長さ・代表面積

この値は STL の外形寸法から自動計算された `Lref`, `Aref` を使っています。

## 11. このシステムで確認済みのこと

今回の調整では、少なくとも次を確認しています。

- `models/2026.stl` で Docker を使ったウェットテストが完走すること
- `models/Part Studio 1 - Part 1.stl` のような空白入りファイル名でも Docker で完走すること
- `checkMesh` が `Mesh OK` を返すこと
- `Cd`, `Cl`, `Cs` がゼロではなく出力されること
- 小型モデル相当のダミー STL でも `--no-docker` で寸法スケーリングと設定生成が通ること
- `0 mm` 地上高の箱モデルでも、自動微小浮上で Docker ウェットテストが完走すること
- `model/` / `models/` の両方に対応していること

## 12. よくある困りごと

### STL が見つからない

- `model/` か `models/` に入っているか確認してください
- 拡張子が `.stl` / `.STL` でも動きます

### Docker エラーが出る

- Docker Desktop が起動しているか確認してください
- もう一度 `run_mac.sh` または `run_windows.bat` を実行してください

### 可視化画像が出ない

- CFD 本体は成功していても、PyVista/VTK の描画環境によって画像生成に失敗することがあります
- その場合でも `VTK/` は出力されるので、ParaView で直接開けば結果確認できます

### 計算が重い

- まずはメッシュ `1` または `2` で試してください
- モデルが大きい、または表面が複雑だと `snappyHexMesh` に時間がかかります

## 13. 補足

このシステムは「まず動かして比較検討できること」を重視した簡易 CFD セットアップです。

厳密な開発用途では、次も必要になる場合があります。

- 入口乱流条件の再調整
- 路面条件の見直し
- 代表面積の手動指定
- 車輪回転やヨー角の追加
- メッシュ独立性確認

まずは本システムで傾向を見て、必要なら詳細条件を追加してください。
