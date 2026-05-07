# Git Fork 配置说明

**配置时间**: 2026-05-07

---

## ✅ Fork 配置完成

### 仓库信息
- **原仓库**: https://github.com/zhutoutoutousan/worldquant-miner
- **你的 Fork**: https://github.com/hongxingshanshan/worldquant-miner
- **本地路径**: C:\WorkSpace\worldquant-miner

### 远程仓库配置
```
origin   → https://github.com/hongxingshanshan/worldquant-miner.git (你的 fork)
upstream → https://github.com/zhutoutoutousan/worldquant-miner.git (原作者仓库)
```

---

## 📝 工作流程

### 1. 日常开发流程

```bash
# 1. 确保在 master 分支
git checkout master

# 2. 从 upstream 拉取最新更新
git fetch upstream

# 3. 合并 upstream 的 master 分支到本地
git merge upstream/master

# 4. 推送到你的 fork
git push origin master
```

### 2. 创建新功能分支

```bash
# 1. 从 master 创建新分支
git checkout -b feature/my-new-feature

# 2. 进行开发和提交
git add .
git commit -m "Add new feature"

# 3. 推送到你的 fork
git push origin feature/my-new-feature

# 4. 在 GitHub 上创建 Pull Request 到原作者仓库
```

### 3. 同步原作者更新

```bash
# 1. 获取 upstream 最新代码
git fetch upstream

# 2. 切换到目标分支
git checkout master

# 3. 合并 upstream 的更新
git merge upstream/master

# 4. 推送到你的 fork
git push origin master
```

---

## 🔧 常用命令

### 查看远程仓库
```bash
git remote -v
```

### 查看分支状态
```bash
git status
git branch -a
```

### 从 upstream 拉取特定分支
```bash
git fetch upstream develop
git checkout -b develop upstream/develop
```

### 删除本地分支
```bash
git branch -d feature/old-feature
```

### 删除远程分支
```bash
git push origin --delete feature/old-feature
```

---

## 🚀 推荐工作流程

### 场景 1: 本地修改和测试

```bash
# 1. 创建开发分支
git checkout -b dev/local-changes

# 2. 进行修改
# ... 编辑文件 ...

# 3. 提交修改
git add .
git commit -m "Local configuration changes"

# 4. 推送到你的 fork
git push origin dev/local-changes
```

### 场景 2: 贡献代码给原作者

```bash
# 1. 从最新的 upstream 创建分支
git fetch upstream
git checkout -b feature/new-feature upstream/master

# 2. 开发新功能
# ... 编写代码 ...

# 3. 提交
git add .
git commit -m "Add amazing feature"

# 4. 推送到你的 fork
git push origin feature/new-feature

# 5. 在 GitHub 上创建 Pull Request
# 访问: https://github.com/hongxingshanshan/worldquant-miner
# 点击 "Compare & pull request"
```

### 场景 3: 保持 fork 更新

```bash
# 定期同步 upstream 的更新
git fetch upstream
git checkout master
git merge upstream/master
git push origin master

# 如果有 develop 分支
git checkout develop
git merge upstream/develop
git push origin develop
```

---

## ⚠️ 注意事项

### 1. 不要直接在 master 分支开发
- ✅ 创建功能分支进行开发
- ✅ 测试通过后再合并到 master
- ❌ 避免直接在 master 分支修改

### 2. 提交前先同步
```bash
# 在提交前，先同步 upstream 的最新代码
git fetch upstream
git merge upstream/master
```

### 3. 保持提交历史清晰
```bash
# 使用有意义的提交信息
git commit -m "Fix: Data field fetcher initialization issue"
git commit -m "Feature: Add PyQT GUI support"
git commit -m "Docs: Update deployment guide"
```

### 4. 处理冲突
```bash
# 如果合并时出现冲突
git status  # 查看冲突文件
# 手动解决冲突后
git add .
git commit -m "Resolve merge conflicts"
```

---

## 📊 分支策略建议

### 主要分支
- **master**: 稳定的生产代码
- **develop**: 开发分支（如果存在）
- **feature/xxx**: 功能分支
- **bugfix/xxx**: 修复分支
- **personal/xxx**: 个人配置分支

### 示例分支结构
```
upstream/master (原作者)
    ↓
origin/master (你的 fork)
    ↓
personal/config (个人配置)
    ↓
feature/new-feature (新功能)
```

---

## 🎯 下一步建议

### 1. 创建个人配置分支
```bash
git checkout -b personal/my-config
# 添加你的个人配置文件
git add .
git commit -m "Add personal configuration"
git push origin personal/my-config
```

### 2. 设置默认推送
```bash
# 设置当前分支跟踪远程分支
git branch --set-upstream-to=origin/master master
```

### 3. 配置 Git 忽略文件
确保 `.gitignore` 包含:
```
# 个人敏感信息
credential.txt
*.log
.env

# IDE 配置
.vscode/
.idea/

# 系统文件
.DS_Store
Thumbs.db
```

---

## 🔗 有用的链接

- **你的 Fork**: https://github.com/hongxingshanshan/worldquant-miner
- **原仓库**: https://github.com/zhutoutoutousan/worldquant-miner
- **创建 Pull Request**: https://github.com/hongxingshanshan/worldquant-miner/pulls
- **查看 Issues**: https://github.com/zhutoutoutousan/worldquant-miner/issues

---

## 📚 Git 学习资源

- [Git 官方文档](https://git-scm.com/doc)
- [GitHub Fork 工作流](https://docs.github.com/en/get-started/quickstart/fork-a-repo)
- [Git 分支管理](https://git-scm.com/book/zh/v2/Git-%E5%88%86%E6%94%AF-%E5%88%86%E6%94%AF%E7%AE%80%E4%BB%8B)

---

**配置完成！现在你可以自由地在自己的 fork 上进行开发和修改了。**
