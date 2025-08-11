# Decorators

Django Ninja provides flexible decorator support to wrap your API operations with additional functionality like caching, logging, authentication checks, or any custom logic.

## Understanding Decorator Modes

Django Ninja supports two modes for applying decorators:


### OPERATION Mode (Default)
- Applied **after** Django Ninja's validation
- Wraps the operation function with validated data
- Has access to parsed and validated parameters
- Useful for: business logic, logging with validated data, post-validation checks

### VIEW Mode
- Applied **before** Django Ninja's validation
- Wraps the entire Django view function
- Has access to the raw Django request
- Useful for: caching, rate limiting, Django middleware-like functionality
- Similar to Django's standard view decorators


## Using `@decorate_view`

The `@decorate_view` decorator allows you to apply Django view decorators to individual endpoints:

```python
from django.views.decorators.cache import cache_page
from ninja import NinjaAPI
from ninja.decorators import decorate_view

api = NinjaAPI()

@api.get("/cached")
@decorate_view(cache_page(60 * 15))  # Cache for 15 minutes
def cached_endpoint(request):
    return {"data": "This response is cached"}
```

You can apply multiple decorators:

```python
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

@api.get("/multi")
@decorate_view(cache_page(300), vary_on_headers("User-Agent"))
def multi_decorated(request):
    return {"data": "Multiple decorators applied"}
```

## Using `add_decorator`

The `add_decorator` method allows you to apply decorators to multiple endpoints at once.

### Router-Level Decorators

Apply decorators to all endpoints in a router:

```python
from ninja import Router

router = Router()

# Add logging to all operations in this router
def log_operation(func):
    def wrapper(request, *args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(request, *args, **kwargs)
        print(f"Result: {result}")
        return result
    return wrapper

router.add_decorator(log_operation)  # OPERATION mode by default

@router.get("/users")
def list_users(request):
    return {"users": ["Alice", "Bob"]}

@router.get("/users/{user_id}")
def get_user(request, user_id: int):
    return {"user_id": user_id}
```

### API-Level Decorators

Apply decorators to all endpoints in your entire API:

```python
from ninja import NinjaAPI

api = NinjaAPI()

# Add CORS headers to all responses (VIEW mode)
def cors_headers(func):
    def wrapper(request, *args, **kwargs):
        response = func(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        return response
    return wrapper

api.add_decorator(cors_headers, mode="view")

# Now all endpoints will have CORS headers
@api.get("/data")
def get_data(request):
    return {"data": "example"}
```

## Practical Examples

### Example 1: Request Timing

```python
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        start = time.time()
        result = func(request, *args, **kwargs)
        duration = time.time() - start
        if isinstance(result, dict):
            result["_timing"] = f"{duration:.3f}s"
        return result
    return wrapper

router = Router()
router.add_decorator(timing_decorator)

@router.get("/slow")
def slow_endpoint(request):
    time.sleep(1)
    return {"message": "done"}
# Returns: {"message": "done", "_timing": "1.001s"}
```

### Example 2: Authentication Check (OPERATION mode)

```python
from functools import wraps

def require_feature_flag(flag_name):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_feature(flag_name):
                return {"error": f"Feature {flag_name} not enabled"}
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

router = Router()
router.add_decorator(require_feature_flag("new_api"))

@router.get("/new-feature")
def new_feature(request):
    return {"feature": "enabled"}
```

### Example 3: Response Caching (VIEW mode)

```python
from django.core.cache import cache
from functools import wraps
import hashlib

def cache_response(timeout=300):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Create cache key from request
            cache_key = hashlib.md5(
                f"{request.path}{request.GET.urlencode()}".encode()
            ).hexdigest()
            
            # Try to get from cache
            cached = cache.get(cache_key)
            if cached:
                return cached
            
            # Call the view
            response = func(request, *args, **kwargs)
            
            # Cache the response
            cache.set(cache_key, response, timeout)
            return response
        return wrapper
    return decorator

router = Router()
router.add_decorator(cache_response(600), mode="view")
```

## Decorator Execution Order

When multiple decorators are applied, they execute in this order:

1. API-level decorators (outermost)
2. Parent router decorators
3. Child router decorators
4. Individual endpoint decorators (innermost)

```python
api = NinjaAPI()
parent_router = Router()
child_router = Router()

api.add_decorator(api_decorator)
parent_router.add_decorator(parent_decorator)
child_router.add_decorator(child_decorator)

@child_router.get("/test")
@decorate_view(endpoint_decorator)
def endpoint(request):
    return {"result": "ok"}

parent_router.add_router("/child", child_router)
api.add_router("/parent", parent_router)

# Execution order:
# 1. api_decorator
# 2. parent_decorator
# 3. child_decorator
# 4. endpoint_decorator
# 5. endpoint function
```

## Async Support

Decorators work with both sync and async views. When you have mixed sync/async endpoints in the same router, you need to create universal decorators that handle both cases.

### Universal Decorators for Mixed Sync/Async Routers

When you have a router with both sync and async endpoints, use `asyncio.iscoroutinefunction()` to detect the function type:

```python
import asyncio
from functools import wraps

def universal_decorator(func):
    if asyncio.iscoroutinefunction(func):
        # Handle async functions
        @wraps(func)
        async def async_wrapper(request, *args, **kwargs):
            # Your async logic here
            result = await func(request, *args, **kwargs)
            if isinstance(result, dict):
                result["decorated"] = True
                result["type"] = "async"
            return result
        return async_wrapper
    else:
        # Handle sync functions  
        @wraps(func)
        def sync_wrapper(request, *args, **kwargs):
            # Your sync logic here
            result = func(request, *args, **kwargs)
            if isinstance(result, dict):
                result["decorated"] = True
                result["type"] = "sync"
            return result
        return sync_wrapper

router = Router()
router.add_decorator(universal_decorator)

@router.get("/async")
async def async_endpoint(request):
    await asyncio.sleep(0.1)
    return {"endpoint": "async"}

@router.get("/sync") 
def sync_endpoint(request):
    return {"endpoint": "sync"}
```

### Async-Only Decorators

For routers with only async endpoints, you can use async decorators directly:

```python
def async_timing_decorator(func):
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        start = time.time()
        result = await func(request, *args, **kwargs)
        duration = time.time() - start
        if isinstance(result, dict):
            result["_timing"] = f"{duration:.3f}s"
        return result
    return wrapper

router = Router()
router.add_decorator(async_timing_decorator)

@router.get("/async")
async def async_endpoint(request):
    await asyncio.sleep(1)
    return {"message": "async done"}
```

### Sync Decorators on Async Views

You can also use sync decorators on async views by handling coroutines:

```python
def sync_decorator(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        result = func(request, *args, **kwargs)
        
        if asyncio.iscoroutine(result):
            # Handle async functions
            async def async_wrapper():
                actual_result = await result
                if isinstance(actual_result, dict):
                    actual_result["sync_decorated"] = True
                return actual_result
            return async_wrapper()
        else:
            # Handle sync functions
            if isinstance(result, dict):
                result["sync_decorated"] = True
            return result
    return wrapper
```

## When to Use Each Mode

### Use VIEW Mode When:
- You need access to the raw Django request
- Implementing caching at the HTTP level
- Adding/modifying HTTP headers
- Implementing rate limiting
- Working with Django middleware patterns

### Use OPERATION Mode When:
- You need access to validated/parsed data
- Implementing business logic decorators
- Adding data to responses
- Logging with type-safe parameters
- Post-validation security checks

## Best Practices

1. **Use `functools.wraps`**: Always use `@wraps(func)` to preserve function metadata

2. **Handle mixed sync/async routers**: When your router has both sync and async endpoints, use `asyncio.iscoroutinefunction(func)` to create universal decorators

3. **Choose the right approach for async**:
   - **Universal decorators**: Best for mixed routers (detect with `iscoroutinefunction`)
   - **Async-only decorators**: Best for async-only routers (simpler, cleaner) 
   - **Sync decorators with coroutine handling**: Useful for legacy decorators

4. **Be mindful of performance**: Decorators add overhead, especially in VIEW mode

5. **Document side effects**: Clearly document what your decorators modify

6. **Keep decorators focused**: Each decorator should have a single responsibility

7. **Test both sync and async**: When using universal decorators, test both sync and async endpoints