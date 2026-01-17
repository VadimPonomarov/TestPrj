from drf_yasg.generators import OpenAPISchemaGenerator

from core.enums import ParserType


class CustomOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    def get_path_parameters(self, path, view_cls):
        parameters = super().get_path_parameters(path, view_cls)
        parser_enum = [choice.value for choice in ParserType]

        for parameter in parameters:
            if getattr(parameter, "name", None) == "parser_type":
                parameter.enum = parser_enum

        return parameters
