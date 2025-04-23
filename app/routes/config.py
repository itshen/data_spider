from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import db, api_client

bp = Blueprint('config', __name__)

@bp.route('/')
def index():
    """显示配置页面"""
    # 获取当前配置
    config = db.get_config()
    
    # 获取所有榜单
    nodes = db.get_all_nodes()
    
    # 按分类整理榜单
    categories = {
        1: {'name': '综合', 'en_name': 'news', 'nodes': []},
        2: {'name': '科技', 'en_name': 'tech', 'nodes': []},
        3: {'name': '娱乐', 'en_name': 'ent', 'nodes': []},
        4: {'name': '社区', 'en_name': 'community', 'nodes': []},
        5: {'name': '购物', 'en_name': 'shopping', 'nodes': []},
        6: {'name': '财经', 'en_name': 'finance', 'nodes': []},
        7: {'name': '开发者', 'en_name': 'developer', 'nodes': []},
        8: {'name': '大学', 'en_name': 'university', 'nodes': []},
        9: {'name': '政务', 'en_name': 'organization', 'nodes': []},
        10: {'name': '博客专栏', 'en_name': 'blog', 'nodes': []},
        11: {'name': '微信公众号', 'en_name': 'wxmp', 'nodes': []},
        12: {'name': '电子报', 'en_name': 'epaper', 'nodes': []},
        13: {'name': '设计', 'en_name': 'design', 'nodes': []},
        0: {'name': '其他', 'en_name': 'other', 'nodes': []},
        -1: {'name': '小工具', 'en_name': 'widget', 'nodes': []}
    }
    
    for node in nodes:
        cid = node.get('cid', 0)
        if cid in categories:
            categories[cid]['nodes'].append(node)
        else:
            categories[0]['nodes'].append(node)
    
    return render_template('config/index.html', 
                           config=config, 
                           categories=categories)

@bp.route('/update_api_key', methods=['POST'])
def update_api_key():
    """更新API密钥"""
    api_key = request.form.get('api_key', '')
    
    # 保存API密钥
    db.update_config(api_key=api_key)
    
    # 测试API密钥
    response = api_client.get_all_nodes(page=1)
    
    if response.get('error'):
        return jsonify({
            'success': False,
            'message': response.get('message')
        })
    else:
        return jsonify({
            'success': True,
            'message': 'API密钥已更新并验证成功'
        })

@bp.route('/update_refresh_interval', methods=['POST'])
def update_refresh_interval():
    """更新刷新间隔"""
    try:
        refresh_interval = int(request.form.get('refresh_interval', 3600))
    except ValueError:
        return jsonify({
            'success': False,
            'message': '无效的刷新间隔值'
        })
    
    # 确保合理的刷新间隔
    if refresh_interval < 300:  # 最小5分钟
        refresh_interval = 300
    
    # 保存刷新间隔
    db.update_config(refresh_interval=refresh_interval)
    
    # 更新任务调度
    from app import scheduler
    from app.tasks import fetch_node_items
    
    # 更新获取榜单内容的任务
    # 将秒转换为小时，但保持最小为12小时
    node_items_hours = max(12, refresh_interval // 3600)
    
    # 移除现有任务
    scheduler.remove_job('fetch_node_items')
    
    # 添加新的任务
    import datetime
    scheduler.add_job(
        id='fetch_node_items',
        func=fetch_node_items,
        trigger='interval',
        hours=node_items_hours,
        next_run_time=datetime.datetime.now() + datetime.timedelta(minutes=1)  # 1分钟后执行第一次
    )
    
    # 热榜内容保持每天一次，不受刷新间隔影响
    
    return jsonify({
        'success': True,
        'message': f'刷新间隔已更新。榜单内容将每 {node_items_hours} 小时更新一次，热榜每天更新一次。'
    })

@bp.route('/update_node_status', methods=['POST'])
def update_node_status():
    """更新榜单启用状态"""
    hashid = request.form.get('hashid')
    is_enabled = request.form.get('is_enabled') == 'true'
    
    if not hashid:
        return jsonify({
            'success': False,
            'message': '缺少榜单ID'
        })
    
    # 更新榜单状态
    db.update_node_status(hashid, is_enabled)
    
    return jsonify({
        'success': True,
        'message': f'榜单状态已更新为 {"启用" if is_enabled else "禁用"}'
    })

@bp.route('/update_node_order', methods=['POST'])
def update_node_order():
    """更新榜单显示顺序"""
    orders = request.json
    
    if not orders:
        return jsonify({
            'success': False,
            'message': '缺少排序数据'
        })
    
    # 更新榜单顺序
    db.update_node_order(orders)
    
    return jsonify({
        'success': True,
        'message': '榜单排序已更新'
    })

@bp.route('/fetch_nodes')
def fetch_nodes():
    """手动获取榜单列表"""
    # 调用获取榜单的任务
    from app.tasks import fetch_all_nodes
    fetch_all_nodes()
    
    return jsonify({
        'success': True,
        'message': '榜单获取完成'
    })

@bp.route('/api_logs')
def api_logs():
    """查看API调用日志"""
    # 获取过滤参数
    page = request.args.get('page', 1, type=int)
    limit = 50
    offset = (page - 1) * limit
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 同时支持endpoint和api_endpoint参数
    endpoint = request.args.get('api_endpoint') or request.args.get('endpoint')
    
    success = None
    if 'success' in request.args:
        success = request.args.get('success') == '1'
    
    # 获取日志数据
    logs = db.get_api_logs(
        limit=limit, 
        offset=offset, 
        start_date=start_date, 
        end_date=end_date, 
        endpoint=endpoint, 
        success=success
    )
    
    # 获取统计数据
    stats = db.get_api_stats(start_date=start_date, end_date=end_date)
    
    return render_template(
        'config/api_logs.html', 
        logs=logs, 
        stats=stats,
        page=page,
        start_date=start_date,
        end_date=end_date,
        endpoint=endpoint,
        success=success
    ) 