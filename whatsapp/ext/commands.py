class Cog:
    def __init__(self):
        pass

    @classmethod
    def listener(cls):
        def decorator(coro):
            setattr(cls, coro.__name__, coro)

            return coro

        return decorator

    @property
    def __cog_name__(self):
        return self.__class__.__name__


class Commands:
    def __init__(self):
        pass


def command():
    def decorator(coro):
        setattr(Commands, coro.__name__, coro)
        return coro

    return decorator


def is_owner():
    pass
