from app import create_app
from app.tasks import register_tasks

app = create_app()

# 注册定时任务
register_tasks()

if __name__ == '__main__':
    # 使用threaded=False避免Flask调试模式下的自动重载导致任务重复执行
    app.run(debug=True, host='0.0.0.0', port=8188, threaded=False, use_reloader=False)