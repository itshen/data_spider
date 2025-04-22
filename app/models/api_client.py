import requests
import json
import logging
import time
from datetime import datetime
from app.models.db import get_config, save_api_log

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = 'https://api.tophubdata.com'

# 记录API信息到日志
def log_api_info():
    """记录API相关信息到日志，便于了解和对账"""
    api_info = """
======================================================
今日热榜API (TopHubData API) 信息
======================================================
基础URL: https://api.tophubdata.com
认证方式: 需要API密钥，通过Authorization请求头传递
用途: 获取各大网站热门榜单数据

主要接口:
1. 获取榜单列表 (/nodes)
   - 方法: GET
   - 参数: p (页码)
   - 用途: 获取所有可用榜单信息

2. 获取榜单内容 (/nodes/{hashid})
   - 方法: GET
   - 用途: 获取指定榜单的最新内容

3. 获取榜单历史 (/nodes/{hashid}/historys)
   - 方法: GET
   - 参数: date (日期)
   - 用途: 获取特定日期的榜单历史数据

4. 搜索内容 (/search)
   - 方法: GET
   - 参数: q (关键词), p (页码), hashid (可选)
   - 用途: 搜索符合关键词的内容

5. 获取热榜内容 (/hot)
   - 方法: GET
   - 参数: date (可选，日期)
   - 用途: 获取综合热榜内容

API密钥获取: https://api.tophubdata.com
======================================================
"""
    logger.info(api_info)

def get_api_key():
    """获取API密钥"""
    config = get_config()
    return config.get('api_key')

def make_request(endpoint, params=None, method='GET'):
    """发送API请求"""
    api_key = get_api_key()
    if not api_key:
        return {'error': True, 'message': 'API密钥未配置'}
    
    url = f"{BASE_URL}/{endpoint}"
    headers = {'Authorization': api_key}
    
    # 记录请求开始时间
    start_time = time.time()
    request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 记录API调用请求信息
    logger.info(f"今日热榜API请求: [{method}] {endpoint} - 参数: {params}")
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params)
        else:
            response = requests.post(url, headers=headers, json=params)
        
        # 计算请求耗时
        elapsed_time = round((time.time() - start_time) * 1000)  # 毫秒
        
        # 尝试解析JSON响应
        try:
            result = response.json()
            success = not result.get('error') and result.get('status') == 200
        except json.JSONDecodeError:
            result = {'error': True, 'message': '服务器返回了无效的JSON响应'}
            success = False
        
        # 记录API调用结果
        status_code = result.get('status', 0)
        status_message = result.get('message', '未知状态')
        
        log_message = (
            f"今日热榜API响应: [{method}] {endpoint} - "
            f"状态: {'成功' if success else '失败'} - "
            f"状态码: {status_code} - "
            f"耗时: {elapsed_time}ms - "
            f"消息: {status_message}"
        )
        
        if success:
            logger.info(log_message)
        else:
            logger.error(log_message)
        
        # 保存API调用日志到数据库
        log_data = {
            'endpoint': endpoint,
            'method': method,
            'params': json.dumps(params) if params else '',
            'success': success,
            'status_code': status_code,
            'response_message': status_message,
            'elapsed_time': elapsed_time,
            'request_time': request_time
        }
        save_api_log(log_data)
        
        # 检查API错误
        if not success:
            return {
                'error': True, 
                'status': status_code,
                'message': f"API错误: {status_code} - {status_message}"
            }
        
        return result
    except requests.RequestException as e:
        error_message = f'请求失败: {str(e)}'
        logger.error(f"今日热榜API异常: [{method}] {endpoint} - {error_message}")
        
        # 保存API调用异常日志到数据库
        log_data = {
            'endpoint': endpoint,
            'method': method,
            'params': json.dumps(params) if params else '',
            'success': False,
            'status_code': 0,
            'response_message': error_message,
            'elapsed_time': round((time.time() - start_time) * 1000),
            'request_time': request_time
        }
        save_api_log(log_data)
        
        return {'error': True, 'message': error_message}

def get_all_nodes(page=1):
    """获取所有榜单信息"""
    return make_request('nodes', params={'p': page})

def get_node_items(hashid):
    """获取指定榜单的最新内容"""
    return make_request(f'nodes/{hashid}')

def get_node_history(hashid, date):
    """获取指定榜单的历史数据"""
    return make_request(f'nodes/{hashid}/historys', params={'date': date})

def search_content(keyword, hashid=None, page=1):
    """搜索内容"""
    params = {'q': keyword, 'p': page}
    if hashid:
        params['hashid'] = hashid
    return make_request('search', params=params)

def get_hot_content(date=None):
    """获取热榜内容"""
    params = {}
    if date:
        params['date'] = date
    return make_request('hot', params=params) 