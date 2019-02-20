import functools
from flask import session, jsonify, g

from ihome.utils.response_code import RET


# 判断用户是否登录
def login_required(f):
    # 被装饰器装饰的函数，默认会更改其__name__属性

    @functools.wraps(f)  # 防止装饰器去装饰函数的时候，被装饰的函数__name__属性被更改的问题
    def wrapper(*args, **kwargs):
        # if 没有登录：
        user_id = session.get("user_id")
        if not user_id:
            # 没有登录直接返回没有登录的JSON
            return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
        else:
            g.user_id = user_id
            # 执行所装饰的函数并返回其响应
            return f(*args, **kwargs)

    return wrapper