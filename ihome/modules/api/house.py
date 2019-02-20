import datetime

from flask import current_app, jsonify, request, g, session
from ihome import sr, db
from ihome.models import Area, House, Facility, HouseImage, Order
from ihome.modules.api import api_blu
from ihome.utils import constants
from ihome.utils.common import login_required
from ihome.utils.constants import AREA_INFO_REDIS_EXPIRES, QINIU_DOMIN_PREFIX, HOUSE_LIST_PAGE_CAPACITY, \
    HOME_PAGE_MAX_HOUSES, HOME_PAGE_DATA_REDIS_EXPIRES
from ihome.utils.image_storage import storage_image
from ihome.utils.response_code import RET


# 我的发布列表
@api_blu.route('/user/houses')
@login_required
def get_user_house_list():
    """
    获取用户房屋列表
    1. 获取当前登录用户id
    2. 查询数据
    :return:
    """
    user_id = g.user_id

    try:
        houses = House.query.filter(House.user_id == user_id).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    houses_dict = []
    for house in houses:
        houses_dict.append(house.to_basic_dict())
    return jsonify(errno=RET.OK, errmsg="OK", data=houses_dict)


# 获取地区信息
@api_blu.route("/areas")
def get_areas():
    """
    1. 查询出所有的城区
    2. 返回
    :return:
    """

    # 先从redis中查询
    try:
        areas_dict = sr.get("areas")
    except Exception as e:
        current_app.logger.error(e)

    if areas_dict:
        return jsonify(errno=RET.OK, errmsg="ok", data=eval(areas_dict))

    try:
        areas = Area.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据错误")

    # 因为不能直接返回对象数组，所以定义一个列表，去中保存每一个模型所对应的字典信息
    areas_dict = []
    # 遍历进行保存
    for area in areas:
        areas_dict.append(area.to_dict())

    # 将数据保存到redis中
    try:
        sr.set("areas", areas_dict, AREA_INFO_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)

    return jsonify(errno=RET.OK, errmsg="ok", data=areas_dict)


# 上传房屋图片
@api_blu.route("/houses/<int:house_id>/images", methods=['POST'])
@login_required
def upload_house_image(house_id):
    """
    1. 取到上传的图片
    2. 进行七牛云上传
    3. 将上传返回的图片地址存储
    4. 进行返回
    :return:
    """

    # 1. 取到上传的图片
    try:
        house_image_file = request.files.get("house_image").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 2. 查询房屋是否存在
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询房屋失败")

    if not house:
        return jsonify(errno=RET.NODATA, errmsg="房屋不存在")

    # 3. 上传到七牛云
    try:
        url = storage_image(house_image_file)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片失败")

    # 4. 初始化房屋的图片模型
    house_image = HouseImage()
    # 设置相关数据
    house_image.house_id = house.id
    house_image.url = url

    # 判断是否有首页图片
    if not house.index_image_url:
        # 保存图片地址
        house.index_image_url = url

    # 更新到数据库
    try:
        db.session.add(house_image)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    return jsonify(errno=RET.OK, errmsg="OK", data={"url": QINIU_DOMIN_PREFIX + url})


# 发布房源
@api_blu.route("/houses", methods=["POST"])
@login_required
def save_new_house():
    """
    1. 接收参数并且判空
    2. 将参数的数据保存到新创建house模型
    3. 保存house模型到数据库
    前端发送过来的json数据
    {
        "title":"",
        "price":"",
        "area_id":"1",
        "address":"",
        "room_count":"",
        "acreage":"",
        "unit":"",
        "capacity":"",
        "beds":"",
        "deposit":"",
        "min_days":"",
        "max_days":"",
        "facility":["7","8"]
    }
    :return:
    """

    # 1. 取到参数

    user_id = g.user_id

    json_dict = request.json
    title = json_dict.get('title')
    price = json_dict.get('price')
    address = json_dict.get('address')
    area_id = json_dict.get('area_id')
    room_count = json_dict.get('room_count')
    acreage = json_dict.get('acreage')
    unit = json_dict.get('unit')
    capacity = json_dict.get('capacity')
    beds = json_dict.get('beds')
    deposit = json_dict.get('deposit')
    min_days = json_dict.get('min_days')
    max_days = json_dict.get('max_days')

    # 1.1 判断是否都有值
    if not all(
            [title, price, address, area_id, room_count, acreage, unit, capacity, beds, deposit, min_days, max_days]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    # 1.2 校验参数格式是否正确
    try:
        price = int(float(price) * 100)
        deposit = int(float(deposit) * 100)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    house = House()
    house.user_id = user_id
    house.area_id = area_id
    house.title = title
    house.price = price
    house.address = address
    house.room_count = room_count
    house.acreage = acreage
    house.unit = unit
    house.capacity = capacity
    house.beds = beds
    house.deposit = deposit
    house.min_days = min_days
    house.max_days = max_days

    # 获取到当前房屋的设施列表数组
    facilities = json_dict.get("facility")
    if facilities:
        house.facilities = Facility.query.filter(Facility.id.in_(facilities)).all()

    # 3.保存house模型到数据库
    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据保存错误")

    return jsonify(errno=RET.OK, errmsg="ok", data={"house_id": house.id})


# 房屋详情
@api_blu.route('/houses/<int:house_id>')
def get_house_detail(house_id):
    """
    1. 通过房屋id查询出房屋模型
    :param house_id:
    :return:
    """
    user_id = session.get("user_id", -1)

    # 先从 redis 中查询
    try:
        house_dict = sr.get("house_info_%d" % house_id)
        if house_dict:
            return jsonify(errno=RET.OK, errmsg="OK", data={"user_id": user_id, "house": eval(house_dict)})
    except Exception as e:
        current_app.logger.error(e)

    # 如果redis中没有查询到
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="房屋信息查询失败")
    if not house:
        return jsonify(errno=RET.NODATA, errmsg="房屋信息不存在")

    # 将数据缓存到redis中
    house_dict = house.to_full_dict()
    try:
        sr.set(("house_info_%d" % house_id), house_dict, constants.HOUSE_DETAIL_REDIS_EXPIRE_SECOND)
    except Exception as e:
        current_app.logger.error(e)
    return jsonify(errno=RET.OK, errmsg="OK", data={"user_id": user_id, "house": house_dict})


# 获取首页展示内容
@api_blu.route('/houses/index')
def house_index():
    """
    获取首页房屋列表
    :return:
    """

    # 先从redis中取
    try:
        houses_dict = sr.get("home_page_house_info")
    except Exception as e:
        houses_dict = None
        current_app.logger.error(e)
    if houses_dict:
        return jsonify(errno=RET.OK, errmsg="OK", data=eval(houses_dict))

    # 查询房屋信息
    try:
        houses = House.query.order_by(House.order_count.desc()).limit(constants.HOME_PAGE_MAX_HOUSES).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据错误")

    houses_dict = []
    for house in houses:
        houses_dict.append(house.to_basic_dict())

    # 将数据缓存到redis中
    try:
        sr.set("home_page_house_info", houses_dict, constants.HOME_PAGE_DATA_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)

    return jsonify(errno=RET.OK, errmsg="OK", data=houses_dict)


# 搜索房屋/获取房屋列表
@api_blu.route('/houses')
def get_house_list():
    # 获取所有的参数
    args = request.args
    area_id = args.get('aid', '')
    start_date_str = args.get('sd', '')
    end_date_str = args.get('ed', '')
    # booking(订单量), price-inc(低到高), price-des(高到低),
    sort_key = args.get('sk', 'new')
    page = args.get('p', '1')

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 日期转换
    try:
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
        # 如果开始时间大于或者等于结束时间，就报错
        if start_date and end_date:
            assert start_date < end_date, Exception("开始时间大于结束时间")
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 从缓存中取出房屋列表
    try:
        redis_key = "houses_%s_%s_%s_%s" % (start_date_str, end_date_str, area_id, sort_key)
        response_data = sr.hget(redis_key, page)
        if response_data:
            return jsonify(errno=RET.OK, errmsg="OK", data=eval(response_data))
    except Exception as e:
        current_app.logger.error(e)

    # 查询数据
    house_query = House.query

    filters = []
    # 判断是否传入城区id
    if area_id:
        filters.append(House.area_id == area_id)

    # 过滤已预订的房屋
    conflict_order = None
    try:
        if start_date and end_date:
            conflict_order = Order.query.filter(Order.begin_date <= end_date, Order.end_date >= start_date).all()
        elif start_date:
            conflict_order = Order.query.filter(Order.end_date >= start_date).all()
        elif end_date:
            conflict_order = Order.query.filter(Order.begin_date <= end_date).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据错误")

    if conflict_order:
        # 取到冲突订单的房屋id
        conflict_house_id = [order.house_id for order in conflict_order]
        # 添加条件：查询出房屋不包括冲突订单中的房屋id
        filters.append(House.id.notin_(conflict_house_id))

    # 根据筛选条件进行排序
    if sort_key == "booking":
        house_query = house_query.filter(*filters).order_by(House.order_count.desc())
    elif sort_key == "price-inc":
        house_query = house_query.filter(*filters).order_by(House.price.asc())
    elif sort_key == "price-des":
        house_query = house_query.filter(*filters).order_by(House.price.desc())
    else:
        house_query = house_query.filter(*filters).order_by(House.create_time.desc())

    # 进行分页
    paginate = house_query.paginate(int(page), constants.HOUSE_LIST_PAGE_CAPACITY, False)
    # 取到当前页数据
    houses = paginate.items
    # 取到总页数
    total_page = paginate.pages
    # 将查询结果转成字符串
    houses_dict = []
    for house in houses:
        houses_dict.append(house.to_basic_dict())

    response_data = {"total_page": total_page, "houses": houses_dict}
    try:
        redis_key = "houses_%s_%s_%s_%s" % (start_date_str, end_date_str, area_id, sort_key)
        # 创建redis管道, 支持多命令事务
        pipe = sr.pipeline()
        # 开启事务
        pipe.multi()
        # 设置数据
        pipe.hset(redis_key, page, response_data)
        # 设置过期时间
        pipe.expire(redis_key, constants.HOUSE_LIST_REDIS_EXPIRES)
        # 提交事务
        pipe.execute()
    except Exception as e:
        current_app.logger.error(e)

    return jsonify(errno=RET.OK, errmsg='请求成功', data=response_data)