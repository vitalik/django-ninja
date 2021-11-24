import importlib
import json

from typing import Any, Optional
from django.core.management.base import BaseCommand, CommandError, CommandParser
from ninja.main import NinjaAPI

from ninja.responses import NinjaJSONEncoder


class Command(BaseCommand):
    help = "Exports Open API schema"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--api",
            dest="api",
            required=True,
            type=str,
            help="Specify api instance module",
        )
        parser.add_argument(
            "--output", dest="output", default=None, type=str, help="Output schema path"
        )

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        path_list = options["api"].split(".")

        if len(path_list) < 2:
            raise CommandError(
                "Module should contains at least package and api instance name attribute!"
            )

        module_path, api_attr = ".".join(path_list[:-1]), path_list[-1]
        try:
            api_module = importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            raise CommandError(f"Module {module_path} not found!")

        api = getattr(api_module, api_attr, None)
        if not api:
            raise CommandError(f"Module '{module_path}' has no attribute '{api_attr}'")
        if not isinstance(api, NinjaAPI):
            raise CommandError(f"{options['api']} is not instance of NinjaAPI!")

        schema = api.get_openapi_schema()
        output = json.dumps(schema, cls=NinjaJSONEncoder)

        if options["output"]:
            with open(options["output"], "wb") as f:
                f.write(output.encode())
        else:
            self.stdout.write(output)
