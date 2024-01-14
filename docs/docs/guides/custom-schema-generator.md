# Custom Schema Generator

**Django Ninja** allows you to custom schema generator by change `NINJA_SCHEMA_GENERATOR_CLASS` in your settings.py

Example Full Qualified Schema Name:

```python
from ninja.schema import NinjaGenerateJsonSchema
from pydantic.json_schema import CoreModeRef, DefsRef


class CustomNinjaGenerateJsonSchema(NinjaGenerateJsonSchema):

    def get_defs_ref(self, core_mode_ref: CoreModeRef) -> DefsRef:
        module_qualname_occurrence_mode = super().get_defs_ref(core_mode_ref)
        name_choices = self._prioritized_defsref_choices[module_qualname_occurrence_mode]
        name_choices.pop(0)
        name_choices.pop(0)
        self._prioritized_defsref_choices[module_qualname_occurrence_mode] = name_choices
        return module_qualname_occurrence_mode
```

In your `settings.py`:

```python
NINJA_SCHEMA_GENERATOR_CLASS = 'path.to.CustomNinjaGenerateJsonSchema'
```
