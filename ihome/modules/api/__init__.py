from flask import Blueprint

# 创建 api_1_0 接口的蓝图
api_blu = Blueprint("api", __name__, url_prefix="/api/v1.0")

from . import passport, profile, house, order
