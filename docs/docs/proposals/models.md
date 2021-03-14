# Models to Schemas

!!! warning ""
    This is just a proposal, and it is **not present in library code**, but eventually this can be a part of Django Ninja.

    Please consider adding likes/dislikes or comments in [github issue](https://github.com/vitalik/django-ninja/issues/17) to express your feelings about this proposal.


## Problem

Schemas are very useful to define your validation rules and responses, but sometimes you need to reflect your database models into schemas and keep changes in sync.

For example, if you have a model and schema:

```Python

class User(models.Model):
    email = models.EmailFiled(max_length=100)
    name = models.CharField(max_length=100, null=True, blank=True)


...

class UserOut(Schema):
    email: str
    name: str = None
```

If you need to extend a database field, you need to remember to add it to the schema as well:

```Python hl_lines="4 11"

class User(models.Model):
    email = models.EmailFiled(max_length=100)
    name = models.CharField(max_length=100, null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)

...

class UserOut(Schema):
    email: str
    name: str = None
    birthdate: date = None

```



## Solution


### ModelSchema

Introduce a **ModelSchema** class that can reflect the Django model:


```Python

from ninja import ModelSchema

class UserOut(ModelSchema):
    class Meta:
        model = User
        fields = ['email', 'name']


# which will create a schema equivalent to:

# class UserOut(Schema):
#     email: str
#     name: str = None
```

### Passing all models fields

If you want to create a schema with **ALL** fields, pass `'__all__'`:

```Python hl_lines="4"
class UserOut(ModelSchema):
    class Meta:
        model = User
        fields = '__all__'
```

OR if you want to pass all fields but **exclude** a few, use `exclude`:

```Python hl_lines="4"
class UserOut(ModelSchema):
    class Meta:
        model = User
        exclude = ['birthdate'] 
        # ^ resulting schema will have only `name` and `email`
```


### Required and not-required fields

For some cases you might want to override which fields are **required or not required** in the API:

```Python
class UserCreate(ModelSchema):
    class Meta:
        model = User
        fields = '__all__'
        required = '__all__'


class UserPatch(ModelSchema):
    class Meta:
        model = User
        fields = '__all__'
        not_required = '__all__'

# will result in these schemas:
#
# class UserCreate(Schema):
#     email: str
#     name: str
#     birthdate: date
# 
# class UserPatch(Schema):
#     email: str = None
#     name: str = None
#     birthdate: date = None

```

You can use `UserPatch` to update only a few fields that were provided in the request.


### Relational fields

If you have fields that are ForeignKey's or ManyToManyField, by default it will map to its primary keys:

```Python hl_lines="4 5 14 20 21"
# model 
class Post():
    title = models.CharField(...)
    owner = models.ForeignKey('auth.User', ...)
    tags = models.ManyToManyField('blog.Tag', blank=True)

...

# schemas

class PostSchema(ModelSchema):
    class Meta:
        model = Post
        fields = '__all__'

# this will produce schema like this:

class PostSchema(ModelSchema):
    title: str
    owner: int
    tags: List[int]

```

If you need to expand to nested models, just define the required schemas:

```Python hl_lines="2 3"
class PostSchema(ModelSchema):
    owner: UserSchema
    tags: List[TagSchema]

    class Meta:
        model = Post
        fields = '__all__'
```


## Issues

By using model generated schemas you will lose the nice IDE support and type checks, but on the other hand, you might not use the attributes directly.


## Your thoughts/proposals

Please give you thoughts/likes/dislikes about this proposal in the [github issue](https://github.com/vitalik/django-ninja/issues/17).


