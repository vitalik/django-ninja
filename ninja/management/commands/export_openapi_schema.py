import json
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.urls.base import resolve
from django.utils.module_loading import import_string

from ninja.main import NinjaAPI
from ninja.management.utils import command_docstring
from ninja.responses import NinjaJSONEncoder


class Command(BaseCommand):
    """
    Example:

        ```terminal
        python manage.py export_openapi_schema
        ```

        ```terminal
        python manage.py export_openapi_schema --api project.urls.api
        ```
    """

    help = "Exports Open API schema"

    def _get_api_instance(self, api_path: Optional[str] = None) -> NinjaAPI:
        if not api_path:
            try:
                return resolve("/api/").func.keywords["api"]  # type: ignore
            except AttributeError:
                raise CommandError(
                    "No NinjaAPI instance found; please specify one with --api"
                )

        try:
            api = import_string(api_path)
        except ImportError:
            raise CommandError(f"Module or attribute for {api_path} not found!")

        if not isinstance(api, NinjaAPI):
            raise CommandError(f"{api_path} is not instance of NinjaAPI!")

        return api

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--api",
            dest="api",
            default=None,
            type=str,
            help="Specify api instance module",
        )
        parser.add_argument(
            "--output",
            dest="output",
            default=None,
            type=str,
            help="Output schema to a file (outputs to stdout if omitted).",
        )
        parser.add_argument(
            "--indent", dest="indent", default=None, type=int, help="JSON indent"
        )
        parser.add_argument(
            "--sorted",
            dest="sort_keys",
            default=False,
            action="store_true",
            help="Sort Json keys",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        api = self._get_api_instance(options["api"])
        schema = api.get_openapi_schema()
        result = json.dumps(
            schema,
            cls=NinjaJSONEncoder,
            indent=options["indent"],
            sort_keys=options["sort_keys"],
        )

        if options["output"]:
            with open(options["output"], "wb") as f:
                f.write(result.encode())
        else:
            self.stdout.write(result)


__doc__ = command_docstring(Command)
