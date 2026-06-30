import unittest
from firefly_cli import registry

class TestRegistry(unittest.TestCase):
    def setUp(self):
        registry._COMMANDS.clear()

    def test_command_decorator_registers(self):
        @registry.command("tx add", help="add a tx")
        def handler(args, ctx):
            return 0
        cmds = registry.all_commands()
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].name, "tx add")
        self.assertIs(cmds[0].handler, handler)

    def test_add_arguments_callback_stored(self):
        def args_cb(p):
            p.add_argument("name")
        @registry.command("account get", args=args_cb)
        def handler(args, ctx):
            return 0
        self.assertIs(registry.all_commands()[0].args, args_cb)
