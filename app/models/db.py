import sqlite3
import time
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect('instance/data.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_config():
    """获取系统配置"""
    with get_db_connection() as conn:
        config = conn.execute('SELECT * FROM configs ORDER BY id LIMIT 1').fetchone()
        return dict(config) if config else {}

def update_config(api_key=None, ip_whitelist=None, refresh_interval=None):
    """更新系统配置"""
    with get_db_connection() as conn:
        if api_key is not None:
            conn.execute('UPDATE configs SET api_key = ? WHERE id = 1', (api_key,))
        if ip_whitelist is not None:
            conn.execute('UPDATE configs SET ip_whitelist = ? WHERE id = 1', (ip_whitelist,))
        if refresh_interval is not None:
            conn.execute('UPDATE configs SET refresh_interval = ? WHERE id = 1', (refresh_interval,))
        conn.commit()

def get_all_nodes():
    """获取所有榜单"""
    with get_db_connection() as conn:
        nodes = conn.execute('SELECT * FROM nodes ORDER BY display_order').fetchall()
        return [dict(node) for node in nodes]

def get_enabled_nodes():
    """获取已启用的榜单"""
    with get_db_connection() as conn:
        nodes = conn.execute('SELECT * FROM nodes WHERE is_enabled = 1 ORDER BY display_order').fetchall()
        return [dict(node) for node in nodes]

def save_node(node_data):
    """保存榜单信息"""
    with get_db_connection() as conn:
        # 检查是否已存在
        existing = conn.execute('SELECT * FROM nodes WHERE hashid = ?', (node_data['hashid'],)).fetchone()
        
        if existing:
            # 更新已有榜单
            conn.execute('''
                UPDATE nodes 
                SET name = ?, display = ?, domain = ?, logo = ?, cid = ?
                WHERE hashid = ?
            ''', (
                node_data['name'], node_data['display'], node_data['domain'],
                node_data['logo'], node_data['cid'], node_data['hashid']
            ))
            
            # 如果存在is_enabled字段，更新启用状态
            if 'is_enabled' in node_data:
                conn.execute('UPDATE nodes SET is_enabled = ? WHERE hashid = ?', 
                             (1 if node_data['is_enabled'] else 0, node_data['hashid']))
        else:
            # 插入新榜单
            max_order = conn.execute('SELECT MAX(display_order) FROM nodes').fetchone()[0] or 0
            conn.execute('''
                INSERT INTO nodes (hashid, name, display, domain, logo, cid, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                node_data['hashid'], node_data['name'], node_data['display'],
                node_data['domain'], node_data['logo'], node_data['cid'],
                max_order + 1
            ))
        conn.commit()

def update_node_status(hashid, is_enabled):
    """更新榜单启用状态"""
    with get_db_connection() as conn:
        conn.execute('UPDATE nodes SET is_enabled = ? WHERE hashid = ?', (1 if is_enabled else 0, hashid))
        conn.commit()

def update_node_order(node_orders):
    """更新榜单显示顺序"""
    with get_db_connection() as conn:
        for hashid, order in node_orders.items():
            conn.execute('UPDATE nodes SET display_order = ? WHERE hashid = ?', (order, hashid))
        conn.commit()

def save_items(node_hashid, items):
    """保存榜单内容项"""
    with get_db_connection() as conn:
        current_time = int(time.time())
        for item in items:
            # 检查是否已存在
            existing = conn.execute('SELECT id FROM items WHERE url = ?', (item['url'],)).fetchone()
            if not existing:
                conn.execute('''
                    INSERT INTO items (node_hashid, title, description, url, thumbnail, extra, time, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    node_hashid, item['title'], item.get('description', ''),
                    item['url'], item.get('thumbnail', ''), item.get('extra', ''),
                    item.get('time', current_time), current_time
                ))
        conn.commit()

def get_latest_items(node_hashid=None, limit=50, offset=0):
    """获取最新内容"""
    with get_db_connection() as conn:
        if node_hashid:
            # 微信榜单特殊处理
            if node_hashid == 'WnBe01o371':
                # 直接查询items表，不做JOIN
                items = conn.execute('''
                    SELECT i.*
                    FROM items i
                    WHERE i.node_hashid = ?
                    ORDER BY CAST(REPLACE(REPLACE(i.extra, '万', '0000'), '.', '') AS INTEGER) DESC
                    LIMIT ? OFFSET ?
                ''', (node_hashid, limit, offset)).fetchall()
                
                # 手动添加节点信息
                result = []
                for item in items:
                    item_dict = dict(item)
                    # 添加节点信息
                    item_dict['name'] = '微信'
                    item_dict['display'] = '24h热文榜'
                    item_dict['domain'] = 'mp.weixin.qq.com'
                    item_dict['logo'] = 'https://file.ipadown.com/tophub/assets/images/media/mp.weixin.qq.com.png'
                    result.append(item_dict)
                return result
            else:
                # 其他榜单正常处理
                items = conn.execute('''
                    SELECT i.*, n.name, n.display, n.domain, n.logo
                    FROM items i
                    JOIN nodes n ON i.node_hashid = n.hashid
                    WHERE i.node_hashid = ?
                    ORDER BY i.time DESC
                    LIMIT ? OFFSET ?
                ''', (node_hashid, limit, offset)).fetchall()
        else:
            items = conn.execute('''
                SELECT i.*, n.name, n.display, n.domain, n.logo
                FROM items i
                JOIN nodes n ON i.node_hashid = n.hashid
                JOIN nodes n2 ON n2.hashid = n.hashid
                WHERE n2.is_enabled = 1
                ORDER BY i.time DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset)).fetchall()
        return [dict(item) for item in items]

def search_items(keyword, node_hashid=None, limit=50, offset=0):
    """搜索内容"""
    with get_db_connection() as conn:
        query = '''
            SELECT i.*, n.name, n.display, n.domain, n.logo
            FROM items i
            JOIN nodes n ON i.node_hashid = n.hashid
            WHERE (i.title LIKE ? OR i.description LIKE ?)
        '''
        params = [f'%{keyword}%', f'%{keyword}%']
        
        if node_hashid:
            query += " AND i.node_hashid = ?"
            params.append(node_hashid)
        
        query += " ORDER BY i.time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        items = conn.execute(query, params).fetchall()
        return [dict(item) for item in items]

def clean_unused_nodes(existing_hashids):
    """清理不再存在的榜单，保留hot_content虚拟榜单"""
    with get_db_connection() as conn:
        # 获取所有榜单的hashid
        all_nodes = conn.execute('SELECT hashid FROM nodes').fetchall()
        all_hashids = [node['hashid'] for node in all_nodes]
        
        # 构建要删除的hashid列表（不包括hot_content和现有的hashid）
        to_delete = []
        for hashid in all_hashids:
            if hashid != 'hot_content' and hashid not in existing_hashids:
                to_delete.append(hashid)
        
        if to_delete:
            # 删除不再存在的榜单
            placeholders = ','.join(['?' for _ in to_delete])
            conn.execute(f'DELETE FROM nodes WHERE hashid IN ({placeholders})', to_delete)
            
            # 同时清理相关榜单内容
            conn.execute(f'DELETE FROM items WHERE node_hashid IN ({placeholders})', to_delete)
            
            conn.commit()
            
        return len(to_delete)

def save_api_log(log_data):
    """保存API调用日志"""
    with get_db_connection() as conn:
        # 检查api_logs表是否存在，不存在则创建
        conn.execute('''
            CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                params TEXT,
                success INTEGER NOT NULL,
                status_code INTEGER,
                response_message TEXT,
                elapsed_time INTEGER,
                request_time TEXT,
                created_at INTEGER
            )
        ''')
        
        # 插入日志记录
        current_time = int(time.time())
        conn.execute('''
            INSERT INTO api_logs (
                endpoint, method, params, success, status_code,
                response_message, elapsed_time, request_time, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log_data['endpoint'],
            log_data['method'],
            log_data['params'],
            1 if log_data['success'] else 0,
            log_data['status_code'],
            log_data['response_message'],
            log_data['elapsed_time'],
            log_data['request_time'],
            current_time
        ))
        
        conn.commit()

def get_api_logs(limit=100, offset=0, start_date=None, end_date=None, endpoint=None, success=None):
    """获取API调用日志，支持分页和筛选"""
    with get_db_connection() as conn:
        query = "SELECT * FROM api_logs WHERE 1=1"
        params = []
        
        # 添加筛选条件
        if start_date:
            query += " AND request_time >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND request_time <= ?"
            params.append(end_date)
            
        if endpoint:
            query += " AND endpoint LIKE ?"
            params.append(f"%{endpoint}%")
            
        if success is not None:
            query += " AND success = ?"
            params.append(1 if success else 0)
        
        # 添加排序和分页
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # 执行查询
        logs = conn.execute(query, params).fetchall()
        return [dict(log) for log in logs]

def get_api_stats(start_date=None, end_date=None):
    """获取API调用统计信息"""
    with get_db_connection() as conn:
        # 构建基本查询
        query = """
            SELECT 
                endpoint,
                COUNT(*) as total_calls,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                AVG(elapsed_time) as avg_time,
                MAX(elapsed_time) as max_time,
                MIN(elapsed_time) as min_time
            FROM api_logs
            WHERE 1=1
        """
        params = []
        
        # 添加日期过滤
        if start_date:
            query += " AND request_time >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND request_time <= ?"
            params.append(end_date)
        
        # 按接口分组
        query += " GROUP BY endpoint ORDER BY total_calls DESC"
        
        # 执行查询
        stats = conn.execute(query, params).fetchall()
        
        # 计算总体统计
        total_query = """
            SELECT 
                COUNT(*) as total_calls,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                AVG(elapsed_time) as avg_time
            FROM api_logs
            WHERE 1=1
        """
        
        if start_date:
            total_query += " AND request_time >= ?"
        
        if end_date:
            total_query += " AND request_time <= ?"
        
        total_stats = conn.execute(total_query, params).fetchone()
        
        return {
            'details': [dict(stat) for stat in stats],
            'summary': dict(total_stats) if total_stats else {}
        } 