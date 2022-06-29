# API Docs

## OpenAPI docs

Once you configured your Ninja API and started runserver -  go to <a href="http://127.0.0.1:8000/api/docs" target="_blank">http://127.0.0.1:8000/api/docs</a>

You will see the automatic, interactive API documentation (provided by the <a href="https://github.com/swagger-api/swagger-ui" target="_blank">OpenAPI / Swagger UI</a>


## CDN vs staticfiles

You are not required to put django ninja to `INSTALLED_APPS`. In that case the interactive UI is hosted by CDN. 

To host docs (Js/css) from your own server - just put "ninja" to INSTALLED_APPS - in that case standard django staticfiles mechanics will host it.

## Switch to Redoc

Use `NINJA_DOCS_VIEW` in Django settings

```python
NINJA_DOCS_VIEW = 'redoc'
```

Then you will see the alternative automatic documentation (provided by <a href="https://github.com/Redocly/redoc" target="_blank">Redoc</a>).

## Hiding docs

In case you do not need to display interactive documetation - set `docs_url` argument to `None`

```Python
api = NinjaAPI(docs_url=None)
```

## Protecting docs

To protect docs with authentication (or decorate for some other use case) use `docs_decorator` argument:

```Python
from django.contrib.admin.views.decorators import staff_member_required

api = NinjaAPI(docs_decorator=staff_member_required)
```