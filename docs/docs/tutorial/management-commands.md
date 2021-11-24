# Management Commands

## Export OpenAPI scheme

Add ninja to `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    ...
    'ninja',
    ...
]
```

Run `python manage.py export_openapi_schema --api project.urls.api`

## Options

- `--help` show command help
- `--api` specify api instance module (optional)
- `--output` specify output file path (optional). You can omit this option to output in stdout.
