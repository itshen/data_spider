# 自媒体热点聚合平台

这是一个基于Flask的自媒体热点聚合平台，可以定期爬取各大自媒体平台的热点内容，并永久保存到本地SQLite数据库中。

## 功能特点

- 自动抓取各大自媒体平台热点内容
- 支持配置API密钥和自定义抓取频率
- 支持选择性启用感兴趣的榜单
- 永久保存所有抓取的内容到本地数据库
- 提供搜索功能，支持关键词搜索和榜单筛选
- 支持查看历史榜单数据
- 响应式UI设计，支持移动端和桌面端

## 技术栈

- 后端：Flask
- 前端：TailwindCSS + jQuery
- 数据库：SQLite
- 定时任务：Flask-APScheduler

## 安装与运行

1. 克隆仓库

```bash
git clone https://github.com/yourusername/data_spider.git
cd data_spider
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 运行应用

```bash
python run.py
```

然后访问 http://127.0.0.1:5000 即可使用。

## 配置说明

1. 在配置页面输入您的API密钥（从 https://api.tophubdata.com 获取）
2. 配置数据刷新频率（建议不低于5分钟）
3. 选择您感兴趣的榜单

## 数据库说明

所有数据存储在 `instance/data.db` SQLite数据库文件中，包括：

- 系统配置信息
- 榜单信息
- 抓取的内容数据

## 开发者说明

### 项目结构

```
data_spider/
├── app/                  # 应用主目录
│   ├── models/           # 数据模型
│   ├── routes/           # 路由控制器
│   ├── static/           # 静态资源
│   ├── templates/        # 模板文件
│   ├── __init__.py       # 应用初始化
│   └── tasks.py          # 定时任务
├── instance/             # 实例目录（数据库文件）
├── run.py                # 应用入口
└── requirements.txt      # 依赖列表
```

### API调用

本项目使用了今日热榜API，详情请参考官方文档：https://api.tophubdata.com 