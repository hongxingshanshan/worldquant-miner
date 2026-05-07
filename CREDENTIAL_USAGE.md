# 🔐 账号密码使用说明

**更新时间**: 2026-05-07

---

## 📋 凭证文件

### 文件位置
```
generation_one/naive-ollama/credential.txt
```

### 文件格式
```json
["13723790476@163.com", "qq369225"]
```

**格式说明**：
- JSON 数组格式
- 第一个元素：用户名（邮箱）
- 第二个元素：密码

---

## 🔧 凭证使用流程

### 1. 加载凭证

**代码位置**: `alpha_generator_ollama.py` 第 82-97 行

```python
def setup_auth(self, credentials_path: str) -> None:
    """Set up authentication with WorldQuant Brain."""
    logging.info(f"Loading credentials from {credentials_path}")
    with open(credentials_path) as f:
        credentials = json.load(f)

    username, password = credentials
    self.sess.auth = HTTPBasicAuth(username, password)
```

**步骤**：
1. 从 `credential.txt` 读取 JSON 数据
2. 解析用户名和密码
3. 设置 HTTP Basic Authentication

---

### 2. 认证过程

**代码位置**: `alpha_generator_ollama.py` 第 91-97 行

```python
logging.info("Authenticating with WorldQuant Brain...")
response = self.sess.post('https://api.worldquantbrain.com/authentication')
logging.info(f"Authentication response status: {response.status_code}")

if response.status_code != 201:
    raise Exception(f"Authentication failed: {response.text}")
```

**认证方式**：
- **API 端点**: `https://api.worldquantbrain.com/authentication`
- **认证方法**: HTTP Basic Authentication
- **成功状态码**: 201 (Created)

---

### 3. 凭证使用场景

#### 场景 1：初始认证
```python
# 程序启动时
generator = AlphaGenerator(args.credentials, args.ollama_url, args.max_concurrent)
# 自动调用 setup_auth() 进行认证
```

#### 场景 2：重新认证
```python
# 当检测到认证过期时（第 624-627 行）
if "authentication credentials" in sim_resp.text.lower():
    self.setup_auth(self.credentials_path)  # Refresh authentication
```

**触发条件**：
- API 返回 401 未授权错误
- 响应中包含 "authentication credentials" 字样

---

## 🌐 API 调用示例

### 认证请求
```python
POST https://api.worldquantbrain.com/authentication
Headers:
  Authorization: Basic base64(username:password)
```

### 数据字段请求
```python
GET https://api.worldquantbrain.com/data-fields
Headers:
  Authorization: Basic base64(username:password)
```

### 模拟测试请求
```python
POST https://api.worldquantbrain.com/simulations
Headers:
  Authorization: Basic base64(username:password)
Body:
  {
    "regular": "rank(close)",
    "type": "REGULAR",
    "settings": {
      "instrumentType": "EQUITY",
      "region": "USA",
      "universe": "TOP3000",
      "delay": 1,
      "decay": 0,
      "neutralization": "INDUSTRY",
      "truncation": 0.08,
      "pasteurization": "ON",
      "unitHandling": "VERIFY",
      "nanHandling": "ON",
      "language": "FASTEXPR",
      "visualization": False
    }
  }
```

---

## 🔒 安全性说明

### 凭证存储
- ✅ **明文存储** - 存储在本地文件中
- ⚠️ **安全风险** - 文件可能被他人访问

### 安全建议

#### 方案 1：环境变量（推荐）
```bash
# 设置环境变量
set WQ_USERNAME=13723790476@163.com
set WQ_PASSWORD=qq369225

# 修改代码读取环境变量
import os
username = os.getenv('WQ_USERNAME')
password = os.getenv('WQ_PASSWORD')
```

#### 方案 2：加密存储
```python
# 使用加密库加密密码
from cryptography.fernet import Fernet

# 加密
key = Fernet.generate_key()
cipher_suite = Fernet(key)
encrypted_password = cipher_suite.encrypt(password.encode())

# 解密
decrypted_password = cipher_suite.decrypt(encrypted_password).decode()
```

#### 方案 3：配置文件权限
```bash
# Windows: 设置文件权限
icacls credential.txt /inheritance:r
icacls credential.txt /grant:r "%USERNAME%:F"
```

---

## 📊 凭证使用统计

### API 调用频率

| 操作 | 频率 | 说明 |
|-----|------|------|
| 认证 | 启动时 + 过期时 | 一次性操作 |
| 获取数据字段 | 每批次 | 生成 Alpha 前获取 |
| 提交模拟 | 每个 Alpha | 测试 Alpha 表达式 |
| 提交 Alpha | 成功的 Alpha | 提交有潜力的 Alpha |

### 认证有效期

- **WorldQuant Brain API** 通常不设置明确的过期时间
- **程序会自动重新认证** 当检测到认证失败时
- **建议**: 长时间运行时，程序会自动处理认证刷新

---

## 🔧 故障排除

### 问题 1: 认证失败

**错误信息**:
```
Authentication failed: {"error": "Invalid credentials"}
```

**解决方案**:
1. 检查 `credential.txt` 格式是否正确
2. 确认用户名和密码是否正确
3. 检查 WorldQuant Brain 账号是否有效

### 问题 2: 认证过期

**错误信息**:
```
401 Unauthorized
"authentication credentials" in response
```

**解决方案**:
- ✅ **自动处理** - 程序会自动重新认证
- 如果持续失败，检查账号状态

### 问题 3: 凭证文件找不到

**错误信息**:
```
FileNotFoundError: credential.txt
```

**解决方案**:
```bash
# 检查文件是否存在
ls generation_one/naive-ollama/credential.txt

# 如果不存在，创建文件
echo '["your_email@worldquant.com", "your_password"]' > generation_one/naive-ollama/credential.txt
```

---

## 📝 凭证管理最佳实践

### ✅ 推荐做法

1. **定期更换密码** - 提高安全性
2. **使用专用账号** - 不要使用个人主账号
3. **监控账号活动** - 定期检查 WorldQuant Brain 账户
4. **备份凭证文件** - 防止意外丢失

### ❌ 避免的做法

1. **不要提交到 Git** - 添加到 `.gitignore`
2. **不要分享凭证** - 保护账号安全
3. **不要使用弱密码** - 使用强密码

---

## 🔍 验证凭证

### 手动测试

```python
import requests
from requests.auth import HTTPBasicAuth
import json

# 读取凭证
with open('generation_one/naive-ollama/credential.txt') as f:
    credentials = json.load(f)

username, password = credentials

# 测试认证
sess = requests.Session()
sess.auth = HTTPBasicAuth(username, password)

response = sess.post('https://api.worldquantbrain.com/authentication')

if response.status_code == 201:
    print("✅ 认证成功")
else:
    print(f"❌ 认证失败: {response.status_code}")
    print(response.text)
```

---

## 📚 相关代码位置

| 文件 | 行号 | 功能 |
|-----|------|------|
| `alpha_generator_ollama.py` | 82-97 | 凭证加载和认证 |
| `alpha_generator_ollama.py` | 624-627 | 自动重新认证 |
| `alpha_generator_ollama.py` | 809-810 | 命令行参数定义 |
| `credential.txt` | - | 凭证存储文件 |

---

## ✅ 总结

### 凭证使用流程：

1. **加载** - 从 `credential.txt` 读取 JSON 格式的用户名和密码
2. **认证** - 使用 HTTP Basic Authentication 向 WorldQuant Brain API 认证
3. **使用** - 所有 API 请求都携带认证信息
4. **刷新** - 认证过期时自动重新认证

### 安全建议：

- 使用环境变量或加密存储
- 定期更换密码
- 不要提交到 Git
- 使用专用账号

---

**你的凭证已经正确配置，程序会自动处理认证过程。**
