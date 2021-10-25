import asyncio
import importlib.util
import inspect
import logging as logger
import shlex
import sys
import tempfile
import time

import aiohttp
import qrcode
import webwhatsapi
from selenium.common import exceptions

import utils
from .ext.commands import Cog, Commands

logger.getLogger("urllib3").setLevel(logger.CRITICAL)
logger.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logger.CRITICAL)
logging = logger.getLogger("whatsapp")


class Timeout(Exception):
    pass


class ArgumentError(Exception):
    pass


class Embed:
    def __init__(self, title, description, url):
        self.url = url
        self.image = None
        self.title = title
        self.description = description

    def set_image(self, url):
        self.image = url
        return

    @property
    def to_dict(self):
        data = {
            "path": self.image,
            "url": self.url,
            "title": self.title,
            "description": self.description
        }

        return data


class Bot:
    def __init__(
            self,
            command_prefix
    ):
        self.cog = {}
        self.driver = None
        self.extension = {}
        self.command_prefix = command_prefix
        self.sesi = None

    @staticmethod
    def command():
        logging.debug("Adding command to command_list")

        def decorator(coro):
            setattr(Commands, coro.__name__, coro)
            return coro

        return decorator

    def add_cog(self, cog):
        logging.debug("Adding new cog to cog_list")

        cog_name = cog.__cog_name__
        self.cog[cog_name] = cog

        return

    def event(self, coro):
        logging.debug("Retrieving all event handler")

        setattr(self, coro.__name__, coro)

        return coro

    def load_extension(self, name):
        logging.debug("Importing module")

        name = importlib.util.resolve_name(name, "None")
        spec = importlib.util.find_spec(name)
        lib = importlib.util.module_from_spec(spec)
        sys.modules[name] = lib

        spec.loader.exec_module(lib)

        setup = getattr(lib, "setup")

        setup(self)

        self.extension[name] = lib

        return

    @staticmethod
    def argument_parser(coro, args, args_slice):
        args = shlex.split(args)
        args_spec = inspect.getfullargspec(coro)

        all_availableargs = args_spec.args
        all_availableargs = all_availableargs[args_slice:]

        all_availablekwargs = args_spec.kwonlyargs
        _kwargs = {}

        for i in range(len(all_availableargs)):
            try:
                _kwargs[all_availableargs[i]] = args[i]
            except IndexError:
                raise ArgumentError(f"{all_availableargs[i]} argument is empty")

        for a in range(len(all_availablekwargs)):
            _kwargs[all_availablekwargs[a]] = " ".join(args[len(all_availableargs):])

        return _kwargs

    @staticmethod
    def get_class_that_defined_method(meth):
        if inspect.ismethod(meth) or (
                inspect.isbuiltin(meth) and getattr(meth, '__self__', None) is not None and getattr(meth.__self__,
                                                                                                    '__class__', None)):
            for cls in inspect.getmro(meth.__self__.__class__):
                if meth.__name__ in cls.__dict__:
                    return cls
            meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
        if inspect.isfunction(meth):
            cls = getattr(inspect.getmodule(meth),
                          meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                          None)
            if isinstance(cls, type):
                return cls
        return getattr(meth, '__objclass__', None)  # handle special descriptor objects

    async def call_command_method(self, command_name, message, chat):
        logging.debug("Calling the command function and return it Context class")

        command = getattr(Commands, command_name)
        args = message.content.split(self.command_prefix + command_name)[1]

        if command.__qualname__ == command_name:
            kwargs = self.argument_parser(command, args, 1)
            return await command(Context(self.driver, message, chat, "yt!"), **kwargs)
        else:
            kwargs = self.argument_parser(command, args, 2)
            cogs = self.get_class_that_defined_method(command)

            return await command(
                self.cog[cogs.__name__],
                Context(self.driver, message, chat, "yt!"),
                **kwargs
            )

    async def if_command_available(self, called_command, available_command, message, chat):
        if called_command == available_command:
            return await self.call_command_method(available_command, message, chat)

    async def parse_commands(self, called_command, message, chat):
        logging.debug("Retrieving all available command")

        for available_command in dir(Commands):
            await self.if_command_available(called_command, available_command, message, chat)

        return

    async def check_if_commands(self, chat, message):
        logging.debug("Checking if current message was a command message")

        message_content = message.content

        if message_content.startswith(self.command_prefix):
            prefix_length = len(self.command_prefix)
            command_name = message_content[prefix_length:]
            command_name = command_name.split(" ")
            command_name = command_name[0]

            return await self.parse_commands(command_name, message, chat)
        return

    async def message_looper(self, __chat__):
        logging.debug("Looping through messages")

        for message in __chat__.messages:
            await self.check_if_commands(__chat__.chat, message)

        return

    async def chat_looper(self, chats):
        logging.debug("Looping through chats")

        for __chat__ in chats:
            await self.message_looper(__chat__)

        return

    async def parse_chat(self, chat):
        if chat:
            return await self.chat_looper(chat)

    async def get_chat(self):
        try:
            return self.driver.get_unread()
        except TypeError:
            return None

    async def connect(self):
        logging.debug("Logged")

        self.sesi = aiohttp.ClientSession()

        await self.on_ready()  # type: ignore

        for cog in self.cog:
            await self.cog[cog].on_ready()

        logging.debug("Starting whatsapp websocket...")

        while True:
            chat = await self.get_chat()

            try:
                await self.parse_chat(chat)
            except Exception as e:
                logging.exception(e)

    async def login(self):
        logging.debug("Launching driver")

        try:
            self.driver = webwhatsapi.WhatsAPIDriver(headless=False)
        except exceptions.TimeoutException:
            raise Timeout("Driver timeout")
        except exceptions.NoSuchWindowException:
            print("window error")

            self.driver.quit()
            return False

        logging.debug("Driver launched")

        self.driver.driver.find_element_by_css_selector("._2lolS > label:nth-child(2) > input:nth-child(1)").click()

        qr = self.driver.get_qr_plain()

        qrcode.make(qr).save("qr.png")

        logging.info("Waiting for QR to be scanned")

        logged = False

        while True:
            try:
                logged = self.driver.wait_for_login()
            except exceptions.NoSuchElementException:
                self.driver.driver.refresh()

            if logged:
                return True

            try:
                self.driver.driver.find_element_by_css_selector("._2znac").click()
            except exceptions.NoSuchElementException:
                pass

            try:
                qr = self.driver.get_qr_plain()
            except exceptions.NoSuchElementException:
                self.driver.driver.refresh()

            qrcode.make(qr).save("qr.png")

    async def login_loop(self):
        logging.debug("Starting login session")

        logged = await self.login()

        if logged:
            return True

        if logged is None:
            return None

        return time.sleep(60)

    async def main(self):
        logging.debug("Starting login loop")

        while not await self.login_loop():
            pass

        try:
            await self.connect()
        except KeyboardInterrupt:
            return await self.disconnect()

    async def disconnect(self):
        logging.debug("Quitting driver...")
        await self.sesi.close()

    def run(self):
        logging.debug("Starting event loop")

        loop = asyncio.get_event_loop()

        return loop.run_until_complete(self.main())


class Context(Bot):
    def __init__(self, driver, message, chat, command_prefix):
        super().__init__(command_prefix)
        self.driver = driver
        self.chatid = chat.id
        self.__timestamp__ = message.timestamp

    async def send(self, *content, embed: Embed = None):
        logging.debug("Sending message...")

        content = " ".join(content)

        if embed:
            embed_data = embed.to_dict
            image_path = embed_data["path"]

            if image_path.startswith("http"):
                sesi = utils.Connection(self.sesi)  # type: ignore
                data = await sesi.handler(image_path, respon=True)
                f = tempfile.TemporaryFile()
                f.write(data.content)
                embed_data["path"] = f.name

            return self.driver.send_message_with_thumbnail(chatid=self.chatid, text=content, **embed_data)
        else:
            return self.driver.send_message_to_id(recipient=self.chatid, message=content)

    @property
    def timestamp(self):
        logging.debug("Returning context timestamp")

        return self.__timestamp__
