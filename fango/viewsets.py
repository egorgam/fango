import inspect
from copy import deepcopy
from types import FunctionType, MethodType, UnionType
from typing import Generic, TypeVar, cast

from django.db.models import QuerySet
from fastapi import Request
from fastapi.routing import APIRoute
from pydantic import BaseModel

from fango.generics import BaseModelT
from fango.permissions import ALLOW_ANY
from fango.routing import FangoRouter, action
from fango.schemas import ActionClasses
from fango.utils import copy_instance_method


class AsyncGenericViewSet(Generic[BaseModelT]):
    """
    Async Generic ViewSet implementation.

    """

    _internal = FangoRouter()
    pydantic_model: BaseModelT
    payload_pydantic_model: BaseModelT | None = None
    queryset: QuerySet
    http_method_names: set[str]
    lookup_value_converter: str = "int"
    pydantic_model_action_classes: ActionClasses = {}

    def __init__(self, router: FangoRouter, basename: str) -> None:
        self.request: Request
        self._router = router
        self._basename = basename
        self.__initialize_http_methods()
        self.__initialize_pydantic_model_classes()
        self.__merge_routers()

    def __initialize_http_methods(self) -> None:
        RO_METHODS = {"HEAD", "TRACE", "OPTIONS", "GET"}
        RW_METHODS = {"PATCH", "POST", "PUT", "DELETE"}

        if hasattr(self, "queryset") and self.queryset.model._meta.managed:
            self.http_method_names = RO_METHODS | RW_METHODS
        else:
            self.http_method_names = RO_METHODS

    def __initialize_pydantic_model_classes(self) -> None:
        """
        Method for init pydantic_model_action_classes for all viewset routes.

        """
        action_classes = ActionClasses({x.name: self.pydantic_model for x in self._internal.routes})  # type: ignore
        action_classes.update(self.pydantic_model_action_classes)
        self.pydantic_model_action_classes = action_classes

    def __merge_routers(self) -> None:
        """
        Method for merge viewset internal router with true API router.

        • Original "route.endpoint" with klass method is replaced by instance method
        • Original response_schema is replaced bi instance response_schema
        • @action routes included to viewset internal router

        """
        exclude = self.__patch_routes_in_action_router()
        self.__include_internal_router(exclude)

    def __patch_routes_in_action_router(self) -> set[str]:
        """
        Process @action router.

        """
        exclude = set()
        for route in action.routes:
            route = cast(APIRoute, route)

            if self.__class__.__name__ in route.endpoint.__qualname__ and route.endpoint.__module__ == self.__module__:
                if ALLOW_ANY not in route.dependencies:
                    route.dependencies = self._router.dependencies

                route.endpoint = getattr(self, route.name)
                route.path = f"{self._router.prefix}/{self._basename}{route.path}"
                route.tags = [self._basename]
                exclude.add(route.name)

        return exclude

    def __include_internal_router(self, exclude: set[str]) -> None:
        """
        Process @internal router per viewset.

        """

        router = deepcopy(self._internal)
        router.routes = [
            route
            for route in router.routes
            if route.name not in exclude  # type: ignore
            and route.methods & self.http_method_names  # type: ignore
        ]
        for route in router.routes:
            route = cast(APIRoute, route)

            if "%s" in route.path:
                route.path = route.path % self.lookup_value_converter
                route.path_format = route.path_format % self.lookup_value_converter

            route.endpoint = self.__get_route_endpoint(route)

            if route.response_model:
                self.__fix_generic_response_annotations(route)

        self._router.include_router(router=router, prefix=f"/{self._basename}", tags=[self._basename])

    def __get_route_endpoint(self, route: APIRoute) -> MethodType:
        """
        Method returns route endpoint method from ViewSet instance.

        Any methods with Generic annotated params will be replaced by
        runtime created method and function with true pydantic model.

        """

        function_signature = inspect.signature(cast(FunctionType, route.endpoint))
        method = getattr(self, route.name)

        for param in function_signature.parameters.values():
            if isinstance(param.annotation, TypeVar):
                parameters = function_signature.parameters.copy()

                parameters[param.name] = function_signature.parameters[param.name].replace(
                    annotation=self.payload_pydantic_model or self.pydantic_model
                )
                method = copy_instance_method(method)
                method.__func__.__signature__ = function_signature.replace(parameters=tuple(parameters.values()))

        return method

    def __fix_generic_response_annotations(self, route: APIRoute) -> None:
        """
        Fix generic annotations like T -> MyModel
        Fix iterable generic response annotations like Page[T] -> Page[MyModel]

        """
        pydantic_model = self.pydantic_model_action_classes[route.name]

        if isinstance(route.response_model, TypeVar):
            route.response_model = pydantic_model

        elif not isinstance(route.response_model, UnionType):
            for klass in inspect.getmro(route.response_model)[1:]:
                if issubclass(klass, Generic) and issubclass(klass, BaseModel):
                    if route.response_model.__pydantic_generic_metadata__.get("args"):
                        route.response_model = klass[pydantic_model]  # type: ignore
                    else:
                        route.response_model = klass
                    break

    def get_pydantic_model_class(self, request: Request) -> BaseModelT:
        """
        Method for get concrete pydantic_model for route.

        """
        return self.pydantic_model_action_classes[request.scope["route"].name]

    def get_queryset(self, request: Request) -> QuerySet:
        """
        Method for get queryset defined in ViewSet.

        """
        return self.queryset


class CreateUpdateMixin(Generic[BaseModelT]):
    queryset: QuerySet

    async def create_entry(self, payload: BaseModelT) -> int:
        """
        Method for create new entry.

        """
        instance = await self.queryset.model.from_schema(payload)
        await instance.asave()
        return instance.pk

    async def update_entry(self, payload: BaseModelT, pk: int):
        """
        Method for update existance entry.

        """
        instance = await self.queryset.model.from_schema(payload, pk)
        await instance.asave()
