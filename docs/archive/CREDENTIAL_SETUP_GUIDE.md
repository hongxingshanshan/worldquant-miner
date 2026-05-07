# WorldQuant Brain 凭证配置指南

## 凭证文件位置
`generation_one\naive-ollama\credential.txt`

## 文件格式
```json
["your.email@worldquant.com", "your_password"]
```

## 配置步骤

### 1. 打开凭证文件
用文本编辑器打开：
```
generation_one\naive-ollama\credential.txt
```

### 2. 替换内容
将文件内容修改为：
```json
["你的邮箱@worldquant.com", "你的密码"]
```

**示例**:
```json
["john.doe@example.com", "MySecurePassword123"]
```

### 3. 保存文件
保存并关闭文件

## 重要提示

⚠️ **安全注意事项**:
1. **不要**将凭证文件上传到 GitHub
2. **不要**与他人分享你的凭证
3. 凭证文件已添加到 `.gitignore`
4. 定期更换密码以确保安全

## 验证凭证

配置完成后，可以运行以下命令验证：

```bash
cd generation_one\naive-ollama
python -c "import json; creds = json.load(open('credential.txt')); print(f'Email: {creds[0]}')"
```

## 获取 WorldQuant Brain 账号

如果你还没有账号：

1. 访问: https://platform.worldquantbrain.com
2. 点击 "Sign Up" 或 "Register"
3. 填写注册信息
4. 验证邮箱
5. 登录并获取凭证

## 故障排除

### 问题 1: 认证失败
**错误**: `Authentication failed: 401`

**解决**:
- 检查邮箱和密码是否正确
- 确认账号是否已激活
- 检查网络连接
- 确认 WorldQuant 服务是否正常

### 问题 2: 文件格式错误
**错误**: `JSONDecodeError`

**解决**:
- 确保文件格式正确: `["email", "password"]`
- 使用英文引号 `"` 而不是中文引号 `""`
- 确保没有多余的空格或换行

### 问题 3: 文件权限问题
**错误**: `Permission denied`

**解决**:
- 以管理员身份运行
- 检查文件是否被其他程序占用
- 确认文件路径正确

## 下一步

凭证配置完成后，运行：

```bash
setup_dependencies.bat
```

---

**配置完成后，请继续下一步：安装 Python 依赖**
