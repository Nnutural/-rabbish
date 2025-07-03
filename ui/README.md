# 聊天应用程序

这是一个基于PyQt6和Web技术的聊天应用程序，包含登录系统和主聊天界面。

## 功能特性

- 🔐 用户登录/注册界面
- 💬 主聊天应用程序
- 🔄 无缝页面跳转
- 🎨 现代化UI设计

## 文件结构

```
ui/
├── app.py              # 主应用程序入口
├── login.py            # 独立的登录页面
├── main.py             # 独立的主应用程序
├── login.html          # 登录页面HTML
├── login.css           # 登录页面样式
├── login.js            # 登录页面脚本
├── index.html          # 主应用程序HTML
├── style.css           # 主应用程序样式
├── backend.py          # 后端API
├── message_storage.py  # 消息存储
├── qwebchannel.js      # WebChannel通信
└── test_app.py         # 测试脚本
```

## 安装依赖

确保已安装PyQt6和相关依赖：

```bash
pip install PyQt6 PyQt6-WebEngine
```

## 运行应用程序

### 方法1：使用主应用程序（推荐）

运行包含登录跳转功能的完整应用程序：

```bash
python app.py
```

### 方法2：独立运行

分别运行登录页面和主应用程序：

```bash
# 运行登录页面
python login.py

# 运行主应用程序
python main.py
```

## 使用说明

### 主应用程序 (app.py)

1. **启动应用**：运行 `python app.py`
2. **登录界面**：应用启动后显示登录页面
3. **输入凭据**：输入任意用户名和密码
4. **点击登录**：点击登录按钮
5. **自动跳转**：登录成功后自动跳转到主聊天界面

### 登录功能

- 支持用户名和密码验证
- 实时输入验证
- 密码显示/隐藏切换
- 登录/注册表单切换

### 主应用程序功能

- 聊天界面
- 消息发送和接收
- 实时通信
- 消息历史记录

## 测试

运行测试脚本验证应用程序配置：

```bash
python test_app.py
```

测试脚本会检查：
- 必要文件是否存在
- 模块导入是否成功
- 依赖项是否完整

## 技术架构

- **前端**：HTML5 + CSS3 + JavaScript
- **后端**：Python + PyQt6
- **通信**：QWebChannel
- **界面**：QWebEngineView + QStackedWidget

## 开发说明

### 页面跳转机制

应用程序使用 `QStackedWidget` 管理多个页面：

1. **登录页面**：索引 0
2. **主应用程序页面**：索引 1

当用户成功登录时，`LoginBackend.loginSuccess()` 方法被调用，触发页面跳转。

### WebChannel通信

- 前端JavaScript通过 `window.backend.loginSuccess()` 调用后端方法
- 后端通过 `@pyqtSlot()` 装饰器暴露方法给前端
- 实现前后端无缝通信

## 故障排除

### 常见问题

1. **模块导入错误**
   - 确保已安装PyQt6和PyQt6-WebEngine
   - 检查Python版本兼容性

2. **页面无法加载**
   - 确保所有HTML、CSS、JS文件存在
   - 检查文件路径是否正确

3. **WebChannel连接失败**
   - 确保qwebchannel.js文件存在
   - 检查浏览器控制台错误信息

### 调试模式

在浏览器开发者工具中查看控制台输出，获取详细的调试信息。

## 许可证

本项目仅供学习和演示使用。 