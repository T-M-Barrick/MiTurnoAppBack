from uuid import uuid4
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from core.exceptions import DomainError, AppSystemError
from core.errores import PYDANTIC_ERROR_MAP, VALIDATORS_CODES_ERROR

logger = logging.getLogger(__name__)

def register_exception_handlers(app):

    @app.exception_handler(DomainError)
    def domain_error_handler(request: Request, exc: DomainError):

        content = {
            "code": exc.code
        }

        if exc.metadata:
            content["metadata"] = exc.metadata

        if exc.field:
            content["field"] = exc.field

        return JSONResponse(
            status_code=exc.status_code,
            content=content
        )
    
    @app.exception_handler(AppSystemError)
    def appsystem_error_handler(request: Request, exc: AppSystemError):

        error_id = uuid4()
        logger.error(f"[{error_id}] AppSystemError: {exc}", exc_info=True)

        content = {
            "code": exc.code,
            "error_id": str(error_id)
        }

        if exc.metadata:
            content["metadata"] = exc.metadata

        return JSONResponse(
            status_code=exc.status_code,
            content=content
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        for err in exc.errors():
            print(err)
        '''
        first_error = exc.errors()[0]
        pydantic_type = first_error["type"]
        field = ".".join(map(str, first_error["loc"][1:]))

        if pydantic_type == "value_error":
            if first_error["msg"] in VALIDATORS_CODES_ERROR:
                code = first_error["msg"]
            else:
                code = "INVALID_INPUT"
                logger.error(f"Error en el Front: {first_error['msg']}")
        else:
            code = PYDANTIC_ERROR_MAP.get(pydantic_type, "INVALID_INPUT")
            if pydantic_type not in PYDANTIC_ERROR_MAP:
                logger.warning(f"Nuevo error Pydantic no mapeado: {pydantic_type}")

        return JSONResponse(
            status_code=422,
            content={
                "code": code,
                "field": field
            }
        )
        '''
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):

        error_id = uuid4()
        logger.exception(f"[{error_id}] {exc}") # a nivel funcional es exactamente lo mismo que hacer logger.error(exc, exc_info=True)

        # Responder al usuario respetando tu formato "message"
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR", # default_message = "Ocurrió un error interno en el servidor"
                "error_id": str(error_id)
            }
        )
