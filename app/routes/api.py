from flask import Blueprint, jsonify, request
from app.models import db, api_client
import time

bp = Blueprint('api', __name__)

@bp.route('/nodes')
def get_nodes():
    """获取所有榜单"""
    nodes = db.get_all_nodes()
    return jsonify(nodes)

@bp.route('/enabled_nodes')
def get_enabled_nodes():
    """获取已启用的榜单"""
    nodes = db.get_enabled_nodes()
    return jsonify(nodes)

@bp.route('/items')
def get_items():
    """获取内容列表"""
    hashid = request.args.get('hashid')
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    
    items = db.get_latest_items(node_hashid=hashid, limit=limit, offset=offset)
    return jsonify(items)

@bp.route('/search')
def search_items():
    """搜索内容"""
    keyword = request.args.get('q', '')
    hashid = request.args.get('hashid')
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    
    if not keyword:
        return jsonify([])
    
    items = db.search_items(keyword, node_hashid=hashid, limit=limit, offset=offset)
    return jsonify(items)

@bp.route('/refresh_node/<hashid>')
def refresh_node(hashid):
    """刷新指定榜单内容"""
    response = api_client.get_node_items(hashid)
    
    if response.get('error'):
        return jsonify({
            'success': False,
            'message': response.get('message')
        })
    
    items = response.get('data', {}).get('items', [])
    
    if items:
        db.save_items(hashid, items)
        return jsonify({
            'success': True,
            'count': len(items),
            'items': items,
            'message': f'成功刷新 {len(items)} 条内容'
        })
    else:
        return jsonify({
            'success': False,
            'message': '未获取到内容'
        })

@bp.route('/refresh_hot')
def refresh_hot():
    """刷新热榜内容"""
    response = api_client.get_hot_content()
    
    if response.get('error'):
        return jsonify({
            'success': False,
            'message': response.get('message')
        })
    
    hot_items = response.get('data', [])
    
    if hot_items:
        hot_node_hashid = 'hot_content'
        
        hot_node = {
            'hashid': hot_node_hashid,
            'name': '今日热榜',
            'display': '榜中榜',
            'domain': 'tophub.today',
            'logo': '',
            'cid': 1
        }
        db.save_node(hot_node)
        
        db.save_items(hot_node_hashid, hot_items)
        
        return jsonify({
            'success': True,
            'count': len(hot_items),
            'message': f'成功刷新 {len(hot_items)} 条热榜内容'
        })
    else:
        return jsonify({
            'success': False,
            'message': '未获取到热榜内容'
        })

@bp.route('/node_history/<hashid>')
def get_node_history(hashid):
    """获取榜单历史数据"""
    date = request.args.get('date')
    
    if not date:
        return jsonify({
            'success': False,
            'message': '缺少日期参数'
        })
    
    response = api_client.get_node_history(hashid, date)
    
    if response.get('error'):
        return jsonify({
            'success': False,
            'message': response.get('message')
        })
    
    history_items = response.get('data', [])
    
    # 保存到数据库
    if history_items:
        db.save_items(hashid, history_items)
    
    return jsonify({
        'success': True,
        'items': history_items,
        'count': len(history_items)
    }) 