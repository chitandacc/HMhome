# 七牛上传文件的工具类
access_key = "kJ8wVO7lmFGsdvtI5M7eQDEJ1eT3Vrygb4SmR00E"
secret_key= "rGwHyAvnlLK7rU4htRpNYzpuz0OHJKzX2O1LWTNl"
bucket_name = "infonews"  # 存储空间名称


def storage_image(data):
    """进行文件上传的工具类"""
    """
       文件上传
       :param data: 上传的文件内容
       :return: 生成的文件名
       """
    import qiniu

    q = qiniu.Auth(access_key, secret_key)
    key = None  # 文件名, 如果不设置, 会生成随机文件名
    token = q.upload_token(bucket_name)
    # 上传文件
    ret, info = qiniu.put_data(token, key, data)
    if ret is not None:
        # 返回文件名
        return ret.get("key")  # 获取生成的随机文件名

    else:
        raise BaseException(info)


if __name__ == '__main__':
    file_name = input("请输入文件名：")
    with open(file_name, "rb") as f:
        storage_image(f.read())

