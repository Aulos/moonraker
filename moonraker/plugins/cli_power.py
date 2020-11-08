import logging
from tornado.ioloop import IOLoop


class CliDevice:
    def __init__(self, dev, config):
        self.name = config.get(dev + "_name", dev)
        self.status = None
        self.server = config.get_server()
        self.shell_command = self.server.lookup_plugin("shell_command")
        self.cmds = {
            "on": config.get(dev + "_on_cmd"),
            "off": config.get(dev + "_off_cmd"),
        }
        self.status_cmd = config.get(dev + "_status_cmd")

    def get_name(self):
        return self.name

    def get_device_info(self):
        return {"device": self.name, "status": self.status, "type": "cli"}

    async def initialize(self):
        await self.refresh_status()

    async def refresh_status(self):
        logging.debug(f"Attempting to check {self.name} status")
        scmd = self.shell_command.build_shell_command(
            self.status_cmd, self._set_device_status
        )
        await scmd.run(timeout=10)

    def _set_device_status(self, data):
        logging.debug(f"For device {self.name} got data: {data}")
        status = data.decode().strip().lower()
        if status not in ("on", "off"):
            raise self.server.error(f"Got bad status from device {self.name}: {status}")
        self.status = status

    async def set_power(self, status):
        await self.power(status)
        await self.refresh_status()

    async def power(self, status):
        await self.shell_command.build_shell_command(self.cmds[status], None).run()


async def load_devices(config):
    server = config.get_server()
    power_plugin = server.load_plugin(config, "power")
    if not power_plugin:
        raise server.error("No power plugin :(")
    dev_names = config.get("devices")
    dev_names = [d.strip() for d in dev_names.split(",") if d.strip()]
    for dev in dev_names:
        await power_plugin.add_device(dev, CliDevice(dev, config))


def load_plugin(config):
    IOLoop.current().spawn_callback(load_devices, config)
