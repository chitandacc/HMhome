# 实现图片验证码和短信验证码的逻辑
import re, random
from flask import request, abort, current_app, jsonify, make_response, json, session

from ihome import sr, db
from ihome.libs.captcha.pic_captcha import captcha
from ihome.models import User
from ihome.modules.api import api_blu
from ihome.utils import constants
from ihome.utils.response_code import RET


# 获取图片验证码
@api_blu.route("/imagecode")
def get_image_code():
    """
    1. 获取传入的验证码编号，并编号是否有值
    2. 生成图片验证码
    3. 保存编号和其对应的图片验证码内容到redis
    4. 返回验证码图片
    :return:
    """
    # current_app.logger.error("error log")
    # 1. 获取传入的验证码编号，并编号是否有值
    args = request.args
    cur = args.get("cur")
    pre = args.get("pre")
    if not cur:
        abort(403)

    # 2. 生成图片验证码
    _, text, image = captcha.generate_captcha()
    current_app.logger.debug(text)
    # 3. 保存编号和其对应的图片验证码内容到redis
    try:
        # 删除之前保存的数据
        sr.delete("ImageCode_" + pre)
        sr.set("ImageCode_" + cur, text, constants.IMAGE_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        # 保存出现错误，返回JSON数据提示错误
        return jsonify(errno=RET.DBERR, errmsg="保存验证码失败")

    # 4. 返回验证码图片
    response = make_response(image)
    response.headers["Content-Type"] = "image/jpg"
    return response


# 获取短信验证码
@api_blu.route('/smscode', methods=["POST"])
def send_sms():
    """
    1. 接收参数并判断是否有值
    2. 校验手机号是正确
    3. 通过传入的图片编码去redis中查询真实的图片验证码内容
    4. 进行验证码内容的比对
    5. 生成发送短信的内容并发送短信
    6. redis中保存短信验证码内容
    7. 返回发送成功的响应
    :return:
    """
    # 1. 接收参数并判断是否有值
    # 取到请求值中的内容
    data = request.data
    data_dict = json.loads(data)
    mobile = data_dict.get("mobile")
    image_code = data_dict.get("image_code")
    image_code_id = data_dict.get("image_code_id")

    if not all([mobile, image_code_id, image_code]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 2. 校验手机号是正确
    if not re.match("^1[3578][0-9]{9}$", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式不正确")

    # 3. 通过传入的图片编码去redis中查询真实的图片验证码内容
    try:
        real_image_code = sr.get("ImageCode_" + image_code_id)
        # 如果能够取出来值，删除redis中缓存的内容
        if real_image_code:
            sr.delete("ImageCode_" + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取图片验证码失败")
    # 3.1 判断验证码是否存在，已过期
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg="验证码已过期")

    # 4. 进行验证码内容的比对
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入错误")

    # 4.1 校验该手机是否已经注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        user = None  # 如果查询时出现错误，也需要给user初始化，如果不初始化，会报未定义的异常
        current_app.logger.error(e)
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg="该手机已被注册")

    # 5. 生成发送短信的内容并发送短信
    result = random.randint(0, 999999)
    sms_code = "%06d" % result
    current_app.logger.debug("短信验证码的内容：%s" % sms_code)
    # result = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], "1")
    # if result != 1:
    #     return jsonify(errno=RET.THIRDERR, errmsg="发送短信失败")

    # 6. redis中保存短信验证码内容
    try:
        sr.set("SMS_" + mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存短信验证码失败")

    # 7. 返回发送成功的响应
    return jsonify(errno=RET.OK, errmsg="发送成功")


# 用户注册
@api_blu.route("/user", methods=["POST"])
def register():
    """
    1. 获取参数和判断是否有值
    2. 从redis中获取指定手机号对应的短信验证码的
    3. 校验验证码
    4. 初始化 user 模型，并设置数据并添加到数据库
    5. 保存当前用户的状态
    6. 返回注册的结果
    :return:
    """

    # 1. 获取参数和判断是否有值
    data_dict = request.json
    mobile = data_dict.get("mobile")
    phonecode = data_dict.get("phonecode")
    password = data_dict.get("password")

    if not all([mobile, phonecode, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 2. 从redis中获取指定手机号对应的短信验证码的
    try:
        sms_code = sr.get("SMS_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取本地验证码失败")

    if not sms_code:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码过期")

    # 3. 校验验证码
    if phonecode != sms_code:
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码错误")

    # 4. 初始化 user 模型，并设置数据并添加到数据库
    user = User()
    user.name = mobile
    user.mobile = mobile
    # 对密码进行处理
    user.password = password

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据保存错误")

    session["user_id"] = user.id
    session["name"] = user.name
    session["mobile"] = user.mobile

    return jsonify(errno=RET.OK, errmsg="注册成功")


# 用户登录
@api_blu.route("/session", methods=["POST"])
def login():
    """
    1. 获取参数和判断是否有值
    2. 从数据库查询出指定的用户
    3. 校验密码
    4. 保存用户登录状态
    5. 返回结果
    :return:
    """

    # 1. 获取参数和判断是否有值
    data_dict = request.json

    mobile = data_dict.get("mobile")
    password = data_dict.get("password")

    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 2. 从数据库查询出指定的用户
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据错误")

    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")

    # 3. 校验密码
    if not user.check_passowrd(password):
        return jsonify(errno=RET.PWDERR, errmsg="密码错误")

    # 4. 保存用户登录状态
    session["user_id"] = user.id
    session["name"] = user.name
    session["mobile"] = user.mobile

    # 5. 返回结果
    return jsonify(errno=RET.OK, errmsg="登录成功")


# 获取登录状态
@api_blu.route('/session')
def check_login():
    """
    检测用户是否登录，如果登录，则返回用户的名和用户id
    :return:
    """
    # 从 session 中取出用户的信息
    user_id = session.get("user_id")
    name = session.get("name")
    # 直接返回
    return jsonify(errno=RET.OK, errmsg="OK", data={"user_id": user_id,"name": name})


# 退出登录
@api_blu.route("/session", methods=["DELETE"])
def logout():
    """
    1. 清除session中的对应登录之后保存的信息
    :return:
    """
    session.pop('user_id', None)
    session.pop('mobile', None)
    session.pop('name', None)

    return jsonify(errno=RET.OK, errmsg="OK")