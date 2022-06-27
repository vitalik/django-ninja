import textwrap
from typing import Type

from django.core.management.base import BaseCommand


def command_docstring(cmd: Type[BaseCommand]) -> str:
    base_args = []
    if cmd is not BaseCommand:  # pragma: no branch
        base_parser = cmd().create_parser("base", "")
        for group in base_parser._action_groups:
            for action in group._group_actions:
                base_args.append(",".join(action.option_strings))
    parser = cmd().create_parser("command", "")
    doc = parser.description or ""

    if cmd.__doc__:  # pragma: no branch
        if doc:  # pragma: no branch
            doc += "\n\n"
        doc += textwrap.dedent(cmd.__doc__)
    args = []
    for group in parser._action_groups:
        for action in group._group_actions:
            if "--help" in action.option_strings:
                continue
            name = ",".join(action.option_strings)
            action_type = action.type
            if not action_type and action.nargs != 0:
                action_type = str
            if action_type:
                if isinstance(action_type, type):  # pragma: no branch
                    action_type = action_type.__name__
                name += f" ({action_type})"
            help = action.help or ""
            if help and not action.required and action.nargs != 0:
                if not help.endswith("."):
                    help += "."
                if action.default is not None:
                    help += f" Defaults to {action.default}."
                else:
                    help += " Optional."
            args.append((name, help))
    # Sort args from this class first, then base args.
    args.sort(key=lambda o: (o[0] in base_args, o[0]))
    if args:  # pragma: no branch
        doc += "\n\nAttributes:"
        for name, description in args:
            doc += f"\n    {name}: {description}"
    return doc
