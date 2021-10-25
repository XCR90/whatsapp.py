from aiohttp import client_exceptions


class Connection:
    def __init__(self, sesi, *args, **kwargs):
        self.sesi = sesi
        self.args = args
        self.kwargs = kwargs

    async def handler(self, *args, **kwargs):
        method = "GET"
        respon = False

        if "method" in kwargs:
            method = kwargs["method"]
        if "respon" in kwargs:
            respon = kwargs["respon"]
        method = getattr(self.sesi, method.lower())
        list(args).append(self.args)
        kwargs.update(self.kwargs)
        respon_data = await method(*args, **kwargs)

        if respon:
            return respon_data

        try:
            return await respon_data.json()
        except client_exceptions.ContentTypeError:
            return await respon_data.text()
