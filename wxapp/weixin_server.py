import requests


class Weixin:
    headers = {
        "Content-Type": "application/json",
    }

    @classmethod
    def getAccessToken(cls, appid: str, secret: str):
        """
        code:
        0       -> ok\n
        40029   -> js_code无效\n
        45011   -> API 调用太频繁，请稍候再试\n
        40226   -> 高风险等级用户，小程序登录拦截\n
        -1      -> 系统繁忙，此时请开发者稍候再试\n
        """
        error_mapping = {
            0: "ok",
            40029: "js_code无效",
            45011: "API 调用太频繁，请稍候再试",
            40226: "高风险等级用户，小程序登录拦截",
            -1: "系统繁忙，此时请开发者稍候再试"
        }
        token_url = "https://api.weixin.qq.com/cgi-bin/token"
        token_params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret
        }
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        errcode = token_data.get("errcode", 0)
        errmsg = token_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        return {
            "access_token": token_data.get("access_token", None),
            "expires_in": token_data.get("expires_in", None)
        }


class Miniapp(Weixin):

    @classmethod
    def loginVerify(cls, appid: str, secret: str, code: str) -> dict:
        """"
        code:
        0       -> ok\n
        40029   -> js_code无效\n
        45011   -> API 调用太频繁，请稍候再试\n
        40226   -> 高风险等级用户，小程序登录拦截\n
        -1      -> 系统繁忙，此时请开发者稍候再试\n
        """

        error_mapping = {
            40029: "code无效",
            45011: "API 调用太频繁，请稍候再试",
            40226: "高风险等级用户，小程序登录拦截",
            -1: "系统繁忙，此时请开发者稍候再试",
            0: "ok",
        }
        verify_url = "https://api.weixin.qq.com/sns/jscode2session"
        verify_params = {
            "grant_type": "authorization_code",
            "appid": appid,
            "secret": secret,
            "js_code": code
        }
        verify_response = requests.get(verify_url, params=verify_params)
        verify_data = verify_response.json()
        errcode = verify_data.get("errcode", 0)
        errmsg = verify_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)

        return {
            "openid": verify_data.get("openid"),
            "unionid": verify_data.get("unionid", None),
            "session_key": verify_data.get("session_key")
        }

    @classmethod
    def getPhoneNumber(cls, access_token: str, code: str) -> dict:
        """"
        code:
        0       -> ok\n
        40029   -> js_code无效\n
        45011   -> API 调用太频繁，请稍候再试\n
        40226   -> 高风险等级用户，小程序登录拦截\n
        -1      -> 系统繁忙，此时请开发者稍候再试\n
        """
        error_mapping = {
            40029: "code 无效",
            45011: "API 调用太频繁，请稍候再试",
            40013: "请求appid身份与获取code的小程序appid不匹配",
            -1: "系统繁忙，请开发者稍候再试",
            0: "ok",
        }
        method_url = f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={access_token}"

        method_data = {
            "code": code
        }

        res = requests.post(method_url, json=method_data)
        res_data = res.json()
        errcode = res_data.get("errcode", 0)
        errmsg = res_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        phone_info = res_data.get("phone_info", {})
        return {
            "mobile": phone_info.get("purePhoneNumber", None),  # 没有区号的手机号
            "country_code": phone_info.get("countryCode", None)  # 区号
        }

    @classmethod
    def sendSubscribeMsg(cls, access_token: str, openid: str, template_id: str, page: str, miniprogram_state: str, data: dict):
        """
        code:
        0       -> ok\n
        40003   -> openid 无效\n
        40037   -> 模板id无效\n
        40038   -> 页面路径无效\n  
        40058   -> 模板数据字段不准确\n

        """

        error_mapping = {
            40003: "openid 无效",
            40037: "模板id无效",
            40038: "页面路径无效",
            40058: "模板数据字段不准确",
            0: "ok",
        }
        send_url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
        send_data = {
            "touser": openid,
            "template_id": template_id,
            "page": page,
            "miniprogram_state": miniprogram_state,
            "lang": "zh_CN",
            "data": data
        }
        send_response = requests.post(send_url, json=send_data)
        send_data = send_response.json()
        errcode = send_data.get("errcode", 0)
        errmsg = send_data.get("errmsg")
        assert int(errcode) == 0, error_mapping.get(errcode, errmsg)
        return send_data
