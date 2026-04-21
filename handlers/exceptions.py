from uuid import uuid4

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from core.logger import logger
from core.exceptions import DomainError, AppSystemError
from core.errores import PYDANTIC_ERROR_MAP

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(DomainError)
    def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:

        content = {
            "code": exc.code,
        }

        if exc.metadata:
            content["metadata"] = exc.metadata

        if exc.field:
            content["field"] = exc.field

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )
    
    @app.exception_handler(AppSystemError)
    def appsystem_error_handler(request: Request, exc: AppSystemError) -> JSONResponse:

        error_id = uuid4()
        logger.error(
            f"[{error_id}] AppSystemError: {exc}", exc_info=(type(exc), exc, exc.__traceback__)
        )

        content = {
            "code": exc.code,
            "error_id": str(error_id),
        }

        if exc.metadata:
            content["metadata"] = exc.metadata

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:

        errores = []

        for err in exc.errors():

            pydantic_type = err["type"]
            field = ".".join(map(str, err["loc"][1:]))

            if pydantic_type == "value_error":
                code = "INVALID_INPUT"
                logger.warning("Error de validación: %s", err["msg"])
            else:
                code = PYDANTIC_ERROR_MAP.get(pydantic_type, "INVALID_INPUT")

                if pydantic_type not in PYDANTIC_ERROR_MAP:
                    logger.warning(f"Nuevo error Pydantic no mapeado: {pydantic_type}")

            errores.append({
                "code": code,
                "field": field,
            })

        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "errors": errores,
            }
        )
        '''
        Ejemplo:
        {
        "code": "VALIDATION_ERROR",
        "errors": [
            {
            "code": "INVALID_INPUT",
            "field": "nombre"
            },
            {
            "code": "STRING_TOO_SHORT",
            "field": "apellido"
            }
        ]
        }
        '''
    
    @app.exception_handler(Exception)
    def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:

        error_id = uuid4()
        logger.error("[%s] Error no manejado", error_id, exc_info=exc)

        # Responder al usuario respetando tu formato "message"
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR", # default_message = "Ocurrió un error interno en el servidor"
                "error_id": str(error_id),
            }
        )