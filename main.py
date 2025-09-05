import inspect, re
from fastapi import FastAPI
from auth_routes import auth_router
from users_routes import user_router
from order_routes import order_router
from categories_routes import category_router
from products_routes import products_router
from product_variants_routes import product_variants_router
from fastapi_jwt_auth import AuthJWT
from schemas import Settings
from fastapi.routing import APIRoute
from fastapi.openapi.utils import get_openapi


app=FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title = "Pizza Delivery API For a Restaurant",
        version = "1.0",
        description = "An API for a Pizza Delivery Service  for a Restaurant",
        routes = app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Enter: **'Bearer &lt;JWT&gt;'**, where JWT is the access token"
        }
    }

    # Get all routes where jwt_optional() or jwt_required
    api_router = [route for route in app.routes if isinstance(route, APIRoute)]

    for route in api_router:
        path = getattr(route, "path")
        endpoint = getattr(route,"endpoint")
        methods = [method.lower() for method in getattr(route, "methods")]

        for method in methods:
            # access_token
            if (
                re.search("jwt_required", inspect.getsource(endpoint)) or
                re.search("fresh_jwt_required", inspect.getsource(endpoint)) or
                re.search("jwt_optional", inspect.getsource(endpoint))
            ):
                openapi_schema["paths"][path][method]["security"] = [
                    {
                        "Bearer Auth": []
                    }
                ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

@AuthJWT.load_config
def get_config():
    return Settings()

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/api/users", tags=["Users"])
app.include_router(order_router, prefix="/api/orders", tags=["Orders"])
app.include_router(category_router, prefix="/api/product-categories", tags=["Categories"])
app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(product_variants_router, prefix="/api/product-variants", tags=["Product Variants"])



