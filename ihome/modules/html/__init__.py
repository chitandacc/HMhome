from flask import Blueprint

# 1. 创建蓝图
html_blu = Blueprint("html", __name__)

# 4. 关联视图函数(避免循环导入)
from .views import *