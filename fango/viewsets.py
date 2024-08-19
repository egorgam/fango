import inspect
from copy import deepcopy
from types import FunctionType, MethodType, UnionType
from typing import Generic, TypeVar, cast

from django.db.models import ProtectedError, QuerySet
from fastapi import HTTPException, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel

from fango.filters import generate_filterset_by_pydantic
from fango.generics import BaseModelT, ModelT
from fango.permissions import PermissionDependency
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
    dependencies = []
    strict_filter_by = None
    read_only: bool = False

    def __init__(self, router: FangoRouter, basename: str) -> None:
        self.pydantic_model = self.__get_pydantic_model_or_table_action_class()
        self.filterset_class = generate_filterset_by_pydantic(self.pydantic_model)
        self._router = router
        self._basename = basename
        self.__initialize_http_methods()
        self.__initialize_pydantic_model_classes()
        self.__process_internal_router()

    def __initialize_http_methods(self) -> None:
        ro_methods = {"HEAD", "TRACE", "OPTIONS", "GET"} | {"PATCH"}
        rw_methods = {"POST", "PUT", "DELETE"}

        if (
            hasattr(self, "queryset")
            and self.queryset.model._meta.managed
            and (self.payload_pydantic_model or not self.read_only)
        ):
            self.http_method_names = ro_methods | rw_methods
        else:
            self.http_method_names = ro_methods

    def __initialize_pydantic_model_classes(self) -> None:
        """
        Method for init pydantic_model_action_classes for all viewset routes.

        """
        action_classes = ActionClasses({x.name: self.pydantic_model for x in self._internal.routes})  # type: ignore
        action_classes.update(self.pydantic_model_action_classes)
        self.pydantic_model_action_classes = action_classes

    def __resolve_dependencies_and_permissions(self, route) -> list:
        """
        Merge route, viewset and @action dependencies and
        resolve permissions priority, then use only max permission.

        """
        dependencies = {*route.dependencies, *self._router.dependencies, *self.dependencies}
        all_applied_permissions = {x for x in dependencies if callable(x) and issubclass(x, PermissionDependency)}

        if permission := {x() for x in dependencies if callable(x)}:
            permission = max(permission).__class__

        return list(dependencies - all_applied_permissions) + [permission]

    def __get_actual_routes_from_action_router(self) -> list[APIRoute]:
        """
        Get actual routes from @action router.

        """
        actions = []
        internal_names = [x.name for x in self._internal.routes]  # type: ignore

        for route in action.routes:
            route = cast(APIRoute, route)

            if hasattr(self, route.name):
                route.endpoint = self.__get_route_endpoint(route)

                if route.name in internal_names:
                    raise Exception(f"@action '{route.name}' collision with viewset method.")

                if route.endpoint == getattr(self, route.name):
                    route.dependencies = self.__resolve_dependencies_and_permissions(route)
                    actions.append(route)

        return actions

    def __process_internal_router(self) -> None:
        """
        Process @internal router per viewset.

        """
        router = deepcopy(self._internal)
        router.routes = [route for route in router.routes if route.methods & self.http_method_names]  # type: ignore

        for route in router.routes:
            route = cast(APIRoute, route)
            route.dependencies = self.__resolve_dependencies_and_permissions(route)

            if "%" in route.path:
                route.path = route.path % self.lookup_value_converter
                route.path_format = route.path_format % self.lookup_value_converter

            route.endpoint = self.__get_route_endpoint(route)
            if route.response_model:
                self.__fix_generic_response_annotations(route)

        router.routes = [*router.routes, *self.__get_actual_routes_from_action_router()]

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

    def __get_pydantic_model_or_table_action_class(self) -> BaseModelT:
        """
        Method for get pydantic model from pydantic_model attr or action class.

        """
        if (
            not hasattr(self, "pydantic_model")
            and hasattr(self, "pydantic_model_action_classes")
            and "list" in self.pydantic_model_action_classes
        ):
            return self.pydantic_model_action_classes["list"]

        elif hasattr(self, "pydantic_model"):
            return self.pydantic_model

        else:
            raise Exception("Method has no pydantic_model.")

    def get_pydantic_model_class(self, request: Request) -> BaseModelT:
        """
        Method for get concrete pydantic_model for route.

        """
        route_name = request.scope["route"].name

        if model := self.pydantic_model_action_classes.get(route_name):
            return model
        else:
            return self.__get_pydantic_model_or_table_action_class()

    async def get_queryset(self, request: Request) -> QuerySet:
        """
        Method for get queryset defined in ViewSet.

        """
        return self.queryset


class CRUDMixin(Generic[BaseModelT, ModelT]):
    queryset: QuerySet

    async def create_entry(self, request: Request, payload: BaseModelT) -> ModelT:
        """
        Method for create new entry.

        """
        return await self.queryset.model.save_from_schema(payload)

    async def update_entry(self, request: Request, payload: BaseModelT, pk: int) -> ModelT:
        """
        Method for update entry.

        """
        return await self.queryset.model.save_from_schema(payload, pk)

    async def delete_entry(self, pk: int) -> None:
        """
        Method for delete entry.

        """

        instance = await self.queryset.aget(pk=pk)

        try:
            await instance.adelete()

        except ProtectedError as e:
            label = self.queryset.model._meta.verbose_name
            relations = "; ".join(f"{x._meta.verbose_name} id={x.pk}" for x in e.protected_objects)

            raise HTTPException(
                status_code=400,
                detail=f"Can't delete object {label} id={pk} by protected relations: {relations}",
            )
