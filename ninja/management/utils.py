import textwrap
from typing import Type

from django.core.management.base import BaseCommand


def command_docstring(cmd: Type[BaseCommand]) -> str:
    base_args = _get_base_args(cmd)
    parser = cmd().create_parser("command", "")

    doc = _build_doc_header(cmd, parser.description or "")

    args = _get_command_args(parser, base_args)
    if args:
        doc += _format_attributes_block(args)

    return doc

def _get_base_args(cmd: Type[BaseCommand]):
    base_args = []

    if cmd is not BaseCommand:  # pragma: no branch
        base_parser = cmd().create_parser("base", "")
        for group in base_parser._action_groups:
            for action in group._group_actions:
                base_args.append(",".join(action.option_strings))

    return base_args


def _build_doc_header(cmd: Type[BaseCommand], description: str) -> str:
    doc = description or ""

    if cmd.__doc__:  # pragma: no branch
        if doc:
            doc += "\n\n"
        doc += textwrap.dedent(cmd.__doc__)

    return doc


def _get_command_args(parser, base_args):
    args = []

    for group in parser._action_groups:
        for action in group._group_actions:
            if "--help" in action.option_strings:
                continue

            args.append(_extract_action_info(action))

    args.sort(key=lambda o: (o[0] in base_args, o[0]))

    return args


def _extract_action_info(action):
    name = ",".join(action.option_strings)
    action_type = _extract_action_type(action)

    if action_type:
        name += f" ({action_type})"

    help_text = _build_help_text(action)

    return (name, help_text)


def _extract_action_type(action):
    action_type = action.type

    if not action_type and action.nargs != 0:
        action_type = str

    if isinstance(action_type, type):  # pragma: no branch
        return action_type.__name__

    return action_type


def _build_help_text(action):
    help_text = action.help or ""

    if help_text and not action.required and action.nargs != 0:
        if not help_text.endswith("."):
            help_text += "."

        if action.default is not None:
            help_text += f" Defaults to {action.default}."
        else:
            help_text += " Optional."

    return help_text


def _format_attributes_block(args):
    block = "\n\nAttributes:"
    for name, description in args:
        block += f"\n    {name}: {description}"
    return block
