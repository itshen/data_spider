from app import scheduler
from app.models import api_client, db
import time
import logging
import datetime

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_tasks():
    """注册所有定时任务"""
    # 注册获取榜单列表的任务
    scheduler.add_job(
        id='fetch_all_nodes',
        func=fetch_all_nodes,
        trigger='interval',
        hours=24,  # 每天获取一次榜单列表
        next_run_time=datetime.datetime.now()  # 立即执行一次
    )
    
    # 注册获取榜单内容的任务
    scheduler.add_job(
        id='fetch_node_items',
        func=fetch_node_items,
        trigger='interval',
        hours=2,  # 每两小时获取一次内容
        next_run_time=datetime.datetime.now() + datetime.timedelta(minutes=1)  # 1分钟后执行第一次
    )
    
    # 注册获取热榜内容的任务
    scheduler.add_job(
        id='fetch_hot_content',
        func=fetch_hot_content,
        trigger='interval',
        hours=24,  # 每天获取一次热榜
        next_run_time=datetime.datetime.now() + datetime.timedelta(minutes=2)  # 2分钟后执行第一次
    )
    
    logger.info("所有定时任务已注册")

def fetch_all_nodes():
    """获取所有榜单列表"""
    logger.info("开始获取榜单列表")
    page = 1
    total_nodes = 0
    all_hashids = set()  # 用于跟踪本次获取的所有榜单hashid
    fetched_pages = set()  # 用于跟踪已获取的页码，避免重复请求
    
    # 清理前先记录用户已启用的榜单
    enabled_nodes = db.get_enabled_nodes()
    enabled_hashids = {node['hashid']: node['is_enabled'] for node in enabled_nodes}
    
    while True:
        # 检查是否已经获取过该页面
        if page in fetched_pages:
            logger.warning(f"页面 {page} 已经获取过，跳过重复请求")
            page += 1
            continue
            
        response = api_client.get_all_nodes(page=page)
        
        # 记录已获取的页面
        fetched_pages.add(page)
        
        if response.get('error'):
            logger.error(f"获取榜单列表失败: {response.get('message')}")
            break
        
        nodes = response.get('data', [])
        if not nodes:
            break
        
        # 保存榜单信息并记录hashid
        for node in nodes:
            hashid = node['hashid']
            all_hashids.add(hashid)
            
            # 如果之前已启用，保持启用状态
            if hashid in enabled_hashids:
                node['is_enabled'] = enabled_hashids[hashid]
                
            db.save_node(node)
            total_nodes += 1
        
        # 检查是否需要继续翻页
        if len(nodes) < 100:
            break
        
        page += 1
    
    # 清理不再存在的榜单（保留hot_content虚拟榜单）
    deleted_count = 0
    if all_hashids:
        deleted_count = db.clean_unused_nodes(all_hashids)
    
    logger.info(f"榜单列表获取完成，共 {total_nodes} 个榜单，清理了 {deleted_count} 个过期榜单")

def fetch_node_items():
    """获取已启用榜单的最新内容"""
    logger.info("开始获取榜单内容")
    
    # 获取所有已启用的榜单
    enabled_nodes = db.get_enabled_nodes()
    
    if not enabled_nodes:
        logger.info("没有启用的榜单，跳过获取内容")
        return
    
    total_items = 0
    
    for node in enabled_nodes:
        logger.info(f"正在获取 {node['name']} - {node['display']} 的内容")
        
        response = api_client.get_node_items(node['hashid'])
        
        if response.get('error'):
            logger.error(f"获取榜单内容失败: {response.get('message')}")
            continue
        
        items = response.get('data', {}).get('items', [])
        
        if items:
            # 保存榜单内容
            db.save_items(node['hashid'], items)
            total_items += len(items)
        
        # 避免请求过于频繁
        time.sleep(1)
    
    logger.info(f"榜单内容获取完成，共 {total_items} 条内容")

def fetch_hot_content():
    """获取热榜内容"""
    logger.info("开始获取热榜内容")
    
    response = api_client.get_hot_content()
    
    if response.get('error'):
        logger.error(f"获取热榜内容失败: {response.get('message')}")
        return
    
    hot_items = response.get('data', [])
    
    if hot_items:
        # 创建一个虚拟的榜单ID用于存储热榜内容
        hot_node_hashid = 'hot_content'
        
        # 确保虚拟榜单存在
        hot_node = {
            'hashid': hot_node_hashid,
            'name': '今日热榜',
            'display': '榜中榜',
            'domain': 'tophub.today',
            'logo': '',
            'cid': 1
        }
        db.save_node(hot_node)
        
        # 保存热榜内容
        db.save_items(hot_node_hashid, hot_items)
        
        logger.info(f"热榜内容获取完成，共 {len(hot_items)} 条内容")
    else:
        logger.info("没有获取到热榜内容") 