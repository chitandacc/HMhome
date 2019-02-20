from datetime import timedelta

from redis import StrictRedis


class Config:  # 定义配置类  封装所有的配置, 方便对配置统一的管理
    # 定义和配置同名的类属性
    DEBUG = True  # 设置调试模式
    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/ihome"  # 数据库连接地址
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 设置追踪数据库变化
    REDIS_HOST = "127.0.0.1"  # redis的ip
    REDIS_PORT = 6379  # redis的端口
    SESSION_TYPE = "redis"  # session存储类型  性能好 方便设置过期时间
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT)  # redis连接对象
    SESSION_USE_SIGNER = True  # 设置sessionid加密  如果加密, 必须设置应用秘钥
    SECRET_KEY = "QLDEP2v5YstktI0qP8SEk3MowGCG4KCegZKhYgZq33HB9dUV0Vb7FVzg30QLf16V"  # 设置应用秘钥
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # 设置session过期时间  默认支持设置过期时间


# 针对不同的编程环境 定义配置子类
class DevelopmentConfig(Config):  # 开发环境
    DEBUG = True


class ProductConfig(Config):  # 生产环境
    DEBUG = False


# 定义字典记录配置的对应关系
config_dict = {
    "dev": DevelopmentConfig,
    "pro": ProductConfig
}
