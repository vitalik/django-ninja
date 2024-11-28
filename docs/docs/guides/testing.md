# Testing

**Django Ninja** is fully compatible with standard [django test client](https://docs.djangoproject.com/en/dev/topics/testing/tools/) , but also provides a test client to make it easy to test just APIs without middleware/url-resolver layer making tests run faster.

To test the following API:
```python
from ninja import NinjaAPI, Schema

api = NinjaAPI()
router = Router()

class HelloResponse(Schema):
    msg: str
    
@router.get("/hello", response=HelloResponse)
def hello(request):
    return {"msg": "Hello World"}

api.add_router("", router)
```

You can use the Django test class:
```python
from django.test import TestCase
from ninja.testing import TestClient

class HelloTest(TestCase):
    def test_hello(self):
        # don't forget to import router from code above
        client = TestClient(router)
        response = client.get("/hello")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"msg": "Hello World"})
```

It is also possible to access the deserialized data using the `data` property:
```python
    self.assertEqual(response.data, {"msg": "Hello World"})
```

## Attributes
Arbitrary attributes can be added to the request object by passing keyword arguments to the client request methods:
```python
class HelloTest(TestCase):
    def test_hello(self):
        client = TestClient(router)
        # request.company_id will now be set within the view
        response = client.get("/hello", company_id=1)
```

### Headers
It is also possible to specify headers, both from the TestCase instantiation and the actual request:
```python
    client = TestClient(router, headers={"A": "a", "B": "b"})
    # The request will be made with {"A": "na", "B": "b", "C": "nc"} headers
    response = client.get("/test-headers", headers={"A": "na", "C": "nc"})
```

### Cookies
It is also possible to specify cookies, both from the TestCase instantiation and the actual request:
```python
    client = TestClient(router, COOKIES={"A": "a", "B": "b"})
    # The request will be made with {"A": "na", "B": "b", "C": "nc"} cookies
    response = client.get("/test-cookies", COOKIES={"A": "na", "C": "nc"})
```

### Users
It is also possible to specify a User for the request:
```python
    user = User.objects.create(...)
    client = TestClient(router)
    # The request will be made with user logged in
    response = client.get("/test-with-user", user=user)
```

## Testing async operations

To test operations in async context use `TestAsyncClient`:

```python
from ninja.testing import TestAsyncClient

client = TestAsyncClient(router)
response = await client.post("/test/")

```
