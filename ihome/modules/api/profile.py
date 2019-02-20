from flask import request, current_app, jsonify, session, g

from ihome import db
from ihome.models import User
from ihome.modules.api import api_blu
from ihome.utils.common import login_required
from ihome.utils.constants import QINIU_DOMIN_PREFIX
from ihome.utils.image_storage import storage_image
from ihome.utils.response_code import RET


# 获取用户信息
@api_blu.route('/user')
@login_required
def get_user_info():
    """
    获取用户信息
    1. 获取到当前登录的用户模型
    2. 返回模型中指定内容
    :return:
    """
    user_id = g.user_id

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据错误")

    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")

    return jsonify(errno=RET.OK, errmsg="OK", data=user.to_dict())


# 修改用户名
@api_blu.route('/user/name', methods=["POST"])
@login_required
def set_user_name():
    """
    0. 判断用户是否登录
    1. 获取到传入参数
    2. 将用户名信息更新到当前用户的模型中
    3. 返回结果
    :return:
    """

    # 1. 获取到传入参数
    data_dict = request.json
    name = data_dict.get("name")
    if not name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")

    # 2. 获取当前登录用户的信息
    user_id = g.user_id

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取用户信息失败")

    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")

    # 更新数据
    user.name = name
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    # 将 session 中保存的数据进行实时更新
    session["name"] = name

    # 返回结果
    return jsonify(errno=RET.OK, errmsg="OK")


# 上传个人头像
@api_blu.route('/user/avatar', methods=['POST'])
@login_required
def set_user_avatar():
    """
    0. 判断用户是否登录
    1. 获取到上传的文件
    2. 再将文件上传到七牛云
    3. 将头像信息更新到当前用户的模型中
    4. 返回上传的结果<avatar_url>
    :return:
    """

    # 0. 判断用户是否登录
    user_id = g.user_id

    # 1. 获取到上传的文件
    try:
        avatar_file = request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 2. 再将文件上传到七牛云
    try:
        url = storage_image(avatar_file)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")

    # 3. 将头像信息更新到当前用户的模型中
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取用户数据错误")

    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")

    # 设置用户模型相关数据
    user.avatar_url = url
    # 将数据保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户数据错误")

    # 4. 返回上传的结果<avatar_url>
    return jsonify(errno=RET.OK, errmsg="OK", data={"avatar_url": QINIU_DOMIN_PREFIX + url})


# 获取用户实名信息
@api_blu.route('/user/auth')
@login_required
def get_user_auth():
    """
    1. 取到当前登录用户id
    2. 通过id查找到当前用户
    3. 获取当前用户的认证信息
    4. 返回信息
    :return:
    """

    user_id = g.user_id

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")

    # auth_dict = {
    #     "real_name": user.real_name,
    #     "id_card": user.id_card
    # }

    return jsonify(errno=RET.OK, errmsg="ok", data=user.to_auth_info())


# 设置用户实名信息
@api_blu.route('/user/auth', methods=["POST"])
@login_required
def set_user_auth():
    """
    1. 取到当前登录用户id
    2. 取到传过来的认证的信息
    3. 通过id查找到当前用户
    4. 更新用户的认证信息
    5. 保存到数据库
    6. 返回结果
    :return:
    """

    # 1. 取到当前登录用户id
    user_id = g.user_id
    # 2. 取到传过来的认证的信息
    data_dict = request.json
    real_name = data_dict.get("real_name")
    id_card = data_dict.get("id_card")

    # 3. 通过id查找到当前用户
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")

    # 4. 更新用户的认证信息
    user.real_name = real_name
    user.id_card = id_card

    # 5. 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    return jsonify(errno=RET.OK, errmsg="OK")
