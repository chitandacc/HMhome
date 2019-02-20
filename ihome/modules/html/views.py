from flask import current_app
from ihome.modules.html import html_blu


# 访问静态文件
@html_blu.route('/<path:file_name>')
def get_html_file(file_name):

    # 判断是否是网站的Logo，如果不是，添加前缀
    if file_name != "favicon.ico":
        file_name = "html/" + file_name

    return current_app.send_static_file(file_name)


# 根路由
@html_blu.route('/')
def index():
    return current_app.send_static_file("html/index.html")