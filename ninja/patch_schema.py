from typing import (
    Any,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, create_model, model_validator

ModelT = TypeVar("ModelT", bound=BaseModel)

# Type alias for patched models to help with type checking
# This allows using cast(PatchedModel, PatchSchema[SomeModel]()) to properly type the model_dump() method
PatchedModel = BaseModel


class PatchSchema(Generic[ModelT]):
    """Generate a patchable version of a Pydantic model.

    Makes all fields optional, but doesn't allow None values unless the field was originally defined as Optional.
    This allows for partial updates where fields can be omitted or provided with legitimate values.

    Example:
        Given a schema:
            class ExampleSchema(BaseModel):
                example_field: str
                optional_field: Optional[str] = None

        PatchSchema[ExampleSchema] will allow:
            - PatchSchema[ExampleSchema]() (no fields provided)
            - PatchSchema[ExampleSchema](example_field="example") (field provided)
            - PatchSchema[ExampleSchema](optional_field=None) (None allowed for originally optional fields)

        But will not allow:
            - PatchSchema[ExampleSchema](example_field=None) (None is not allowed for non-optional fields)

    Usage:
        # Define a regular schema
        class UserSchema(BaseModel):
            name: str
            email: str
            avatar_url: Optional[str] = None

        # Create a patchable version that allows partial updates
        PatchUserSchema = PatchSchema[UserSchema]

        # Use the patched schema for partial updates
        patch_data = PatchUserSchema(name="New Name")  # Only updates the name field
        patch_data = PatchUserSchema(avatar_url=None)  # Can set avatar_url to None since it's optional
    """

    def __new__(
        cls,
        *args: Any,
        **kwargs: Any,
    ) -> "PatchSchema[ModelT]":
        """Cannot instantiate directly."""
        raise TypeError("Cannot instantiate abstract PatchSchema class.")

    def __init_subclass__(
        cls,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Cannot subclass."""
        raise TypeError(f"Cannot subclass {cls.__module__}.PatchSchema")

    @classmethod
    def _is_optional_type(cls, annotation):
        """Check if a type annotation is Optional[X]."""
        if get_origin(annotation) is Union:
            args = get_args(annotation)
            return type(None) in args
        return False

    @classmethod
    def __class_getitem__(
        cls,
        wrapped_class: Type[ModelT],
    ) -> Type[PatchedModel]:
        """Convert model to a patchable model where fields are optional but can't be None unless originally Optional."""

        # Create field definitions for the new model
        fields = {}
        # Keep track of which fields were originally optional
        originally_optional_fields = set()

        # Access model_fields through instance property, not class attribute
        model_fields = getattr(wrapped_class, "model_fields", {})
        for field_name, field_info in model_fields.items():
            # Make the field optional by setting a default value
            annotation = field_info.annotation

            # Check if the field was originally optional
            if cls._is_optional_type(annotation):
                originally_optional_fields.add(field_name)

            fields[field_name] = (Optional[annotation], None)

        # Create the new model class
        class PatchModel(BaseModel):
            model_config = {"extra": "ignore", "arbitrary_types_allowed": True}

            @model_validator(mode="before")
            @classmethod
            def validate_no_none_values(cls, data):
                if isinstance(data, dict):
                    # Check for explicit None values and raise error for non-optional fields
                    for key, value in list(data.items()):
                        if value is None and key not in originally_optional_fields:
                            raise ValueError(f"Field '{key}' cannot be None")
                    # Keep only non-None values
                    return {
                        k: v
                        for k, v in data.items()
                        if v is not None or k in originally_optional_fields
                    }
                return data

            # We don't need a custom schema generator anymore since Pydantic v2 uses anyOf for optional fields

            def model_dump(self, **kwargs) -> Dict[str, Any]:
                # Filter out None values from the serialized object
                # Only include fields that were explicitly set (not default None values)
                dump = super().model_dump(**kwargs)
                # Get fields that were explicitly set (excluding default None values)
                fields_set = self.model_fields_set
                return {k: v for k, v in dump.items() if k in fields_set}

        patched_model = create_model(
            f"Patched{wrapped_class.__name__}", __base__=PatchModel, **fields
        )

        # Pass the originally_optional_fields to the patched model
        patched_model._originally_optional_fields = originally_optional_fields

        # Fix return type by using explicit cast to match the declared return type
        return patched_model  # type: ignore
