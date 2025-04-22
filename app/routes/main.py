from flask import Blueprint, render_template, request, jsonify
from app.models import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """主页，显示所有启用的榜单内容"""
    # 获取所有已启用的榜单
    nodes = db.get_enabled_nodes()
    
    # 获取最新的热点内容
    items = db.get_latest_items(limit=50)
    
    return render_template('index.html', nodes=nodes, items=items)

@bp.route('/node/<hashid>')
def node_detail(hashid):
    """显示单个榜单详情"""
    # 获取榜单信息
    nodes = db.get_all_nodes()
    current_node = next((node for node in nodes if node['hashid'] == hashid), None)
    
    if not current_node:
        return render_template('error.html', message='榜单不存在')
    
    # 获取榜单内容
    items = db.get_latest_items(node_hashid=hashid, limit=200)
    
    return render_template('node_detail.html', node=current_node, items=items, nodes=nodes)

@bp.route('/search')
def search():
    """搜索内容"""
    keyword = request.args.get('q', '')
    hashid = request.args.get('hashid', None)
    
    if not keyword:
        return render_template('search.html', items=[], keyword='')
    
    # 获取所有榜单
    nodes = db.get_all_nodes()
    
    # 搜索内容
    items = db.search_items(keyword, node_hashid=hashid, limit=100)
    
    return render_template('search.html', 
                           items=items, 
                           keyword=keyword, 
                           selected_node=hashid,
                           nodes=nodes)

@bp.route('/api/load_more')
def load_more():
    """加载更多内容"""
    hashid = request.args.get('hashid', None)
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    items = db.get_latest_items(node_hashid=hashid, limit=limit, offset=offset)
    
    # 转换为前端所需格式
    return jsonify({
        'items': items,
        'has_more': len(items) == limit
    }) 