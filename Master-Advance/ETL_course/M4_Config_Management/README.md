# M4 — Config Management

> 「dev 環境連測試 DB、prod 環境連正式 DB」 — 程式一行都不用改

## 為什麼要管 config？

業界鐵律：**程式碼和設定要分開**。

```python
# ❌ 這樣寫死在程式裡，換環境就要改 code
DB_HOST = "192.168.1.50"
DB_PASSWORD = "abc123"

# ✅ 從設定檔讀
config = load_config("config.yaml")
DB_HOST = config["database"]["host"]
DB_PASSWORD = os.environ["DB_PASSWORD"]   # 機密從環境變數來
```

## 三種設定方式的選擇

| 方式 | 適合 | 缺點 |
|:-----|:-----|:-----|
| **INI** (`configparser`) | 簡單 key-value、Python 內建不用裝 | 不支援巢狀、型別全是字串 |
| **YAML** (`pyyaml`) | 巢狀結構、人類可讀、主流 | 縮排錯一格就炸 |
| **.env** (`python-dotenv`) | 機密、環境變數 | 不適合複雜結構 |

**實務組合：** 一般設定用 YAML，機密用 `.env`（而且 `.env` 要加到 `.gitignore`）

## 你會學到

- `configparser` — 讀寫 INI 檔
- `pyyaml` — 讀寫 YAML 檔
- `python-dotenv` + `os.environ` — 管理機密
- **Config 類別** — 用 dataclass 把設定包成型別安全的物件

## 課程檔案

- **`S4_config_management.ipynb`** — INI + YAML + .env 三種方式全講
- **`config/config.ini`** — INI 範例
- **`config/config.yaml`** — YAML 範例
- **`config/.env.example`** — .env 機密範本。複製成 `.env` 後填真實值；
  `.env` 已被 root `.gitignore` 忽略，永遠不會誤 commit 上 GitHub

## 常踩的坑

1. **密碼 commit 上 GitHub** → `.env` 一定要加 `.gitignore`
2. **INI 讀出來全是字串** → `getint()` / `getboolean()` 記得用
3. **YAML 縮排** → 只能用空格不能用 Tab
4. **設定檔找不到** → 用 `pathlib.Path(__file__).parent` 而不是相對路徑
