from flask import Flask
from flask_apscheduler import APScheduler
import os
import sqlite3
import datetime
import logging
from logging.handlers import RotatingFileHandler

# 初始化调度器
scheduler = APScheduler()

def create_app():
    # 创建Flask应用实例
    app = Flask(__name__)
    
    # 配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-for-data-spider'
    app.config['SCHEDULER_API_ENABLED'] = True
    
    # 确保数据目录存在
    os.makedirs('instance', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 配置日志记录
    configure_logging()
    
    # 初始化数据库
    init_db()
    
    # 初始化调度器
    scheduler.init_app(app)
    scheduler.start()
    
    # 记录API信息到日志
    from app.models.api_client import log_api_info
    log_api_info()
    
    # 注册蓝图
    from app.routes import main, api, config
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(config.bp, url_prefix='/config')
    
    # 添加自定义过滤器
    @app.template_filter('datetime')
    def format_datetime(timestamp):
        """格式化时间戳为人类可读格式"""
        if not timestamp:
            return ''
        dt = datetime.datetime.fromtimestamp(int(timestamp))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return app

def init_db():
    """初始化数据库结构"""
    conn = sqlite3.connect('instance/data.db')
    cursor = conn.cursor()
    
    # 创建配置表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT,
        ip_whitelist TEXT,
        refresh_interval INTEGER DEFAULT 3600
    )
    ''')
    
    # 创建榜单表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS nodes (
        hashid TEXT PRIMARY KEY,
        name TEXT,
        display TEXT,
        domain TEXT,
        logo TEXT,
        cid INTEGER,
        is_enabled INTEGER DEFAULT 0,
        display_order INTEGER
    )
    ''')
    
    # 创建内容表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_hashid TEXT,
        title TEXT,
        description TEXT,
        url TEXT UNIQUE,
        thumbnail TEXT,
        extra TEXT,
        time INTEGER,
        created_at INTEGER,
        FOREIGN KEY (node_hashid) REFERENCES nodes (hashid)
    )
    ''')
    
    # 初始化配置
    cursor.execute('SELECT COUNT(*) FROM configs')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO configs (api_key, refresh_interval) VALUES (NULL, 3600)')
    
    conn.commit()
    conn.close()

def configure_logging():
    """配置日志"""
    # 创建日志处理器，写入到文件
    log_file = 'logs/app.log'
    file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # 配置应用日志
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(file_handler)
    
    # 配置Werkzeug日志（Flask的底层库）
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.addHandler(file_handler)
    
    # 配置API客户端日志
    api_logger = logging.getLogger('app.models.api_client')
    api_logger.setLevel(logging.INFO)
    api_logger.addHandler(file_handler)
    
    # 配置任务日志
    task_logger = logging.getLogger('app.tasks')
    task_logger.setLevel(logging.INFO)
    task_logger.addHandler(file_handler) 