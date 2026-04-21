from mappers.common import telefonos, direccion_out, miembro_out, notificaciones_out
from core import models
from schemas import empresa as schemas_empresa

def sucursal_perfil_out(sucursal: models.Sucursal) -> schemas_empresa.SucursalPerfilOut:

    out = schemas_empresa.SucursalPerfilOut(
        id=sucursal.id,
        nombre=sucursal.nombre,
        email=sucursal.email,
        reserva_publica_habilitada=sucursal.reserva_publica_habilitada,
        calificacion=sucursal.calificacion,
        activa=sucursal.activa,
        telefonos=telefonos(sucursal.telefonos),
        direccion=direccion_out(sucursal.direccion),
    )

    return out

# Convierte un objeto de la clase Empresa de SQLAlchemy en uno de clase EmpresaHomeOut de Pydantic
def empresa_home_out(
    empresa: models.Empresa,
    notificaciones: list[models.Notificacion],
    ultimo_cursor_id: int | None,
    miembro_rol: str,
) -> schemas_empresa.EmpresaHomeOut:

    empresa_out = schemas_empresa.EmpresaHomeOut(
        id=empresa.id,
        nombre=empresa.nombre,
        logo_url=empresa.logo_url,
        sucursales=[sucursal_perfil_out(sucursal) for sucursal in empresa.sucursales],
        notificaciones=notificaciones_out(notificaciones, ultimo_cursor_id),
        rol=miembro_rol,
    )

    return empresa_out

# Se le pasa las sucursales como otro argumento en lugar de empresa.sucursales (a diferencia de empresa_home_out)
# porque esta función se usa en modificar_empresa y no se requiere enviar las sucursales
def empresa_perfil_out(empresa: models.Empresa, sucursales: list[models.Sucursal]) -> schemas_empresa.EmpresaPerfilOut:

    empresa_out = schemas_empresa.EmpresaPerfilOut(
        id=empresa.id,
        cuit=empresa.cuit,
        nombre=empresa.nombre,
        email=empresa.email,
        rubro=empresa.rubro,
        rubro2=empresa.rubro2,
        logo_url=empresa.logo_url,
        sucursales=[sucursal_perfil_out(sucursal) for sucursal in sucursales],
    )

    return empresa_out

def empresa_logo_out(logo_url: str) -> schemas_empresa.EmpresaLogoOut:
    return schemas_empresa.EmpresaLogoOut(logo_url=logo_url)

def miembro_empresa_out(miembro: models.Miembro_Empresa) -> schemas_empresa.MiembroEmpresaOut:

    out = schemas_empresa.MiembroEmpresaOut(
        miembro=miembro_out(miembro),
        rol=miembro.rol.nombre,
    )

    return out

def sucursal_de_miembro(miembro: models.Miembro_Sucursal) -> schemas_empresa.SucursalDeMiembro:

    out = schemas_empresa.SucursalDeMiembro(
        id=miembro.sucursal.id,
        nombre=miembro.sucursal.nombre,
        rol=miembro.rol.nombre,
    )

    return out

def miembro_sucursal_out(miembros: list[models.Miembro_Sucursal]) -> schemas_empresa.MiembroSucursalOut:
    if not miembros: # innecesario pero por las dudas si después se modifica código, esto protege de que no explote
        raise ValueError("La función mappers_empresa.miembro_sucursal_out no puede recibir una lista vacía")

    # Tomamos un miembro cualquiera para obtener los datos del usuario
    primer_miembro = miembros[0]

    out = schemas_empresa.MiembroSucursalOut(
        miembro=miembro_out(primer_miembro),
        sucursales=[sucursal_de_miembro(m) for m in miembros],
    )

    return out

def agrupar_miembros_por_usuario(miembros: list[models.Miembro_Sucursal]) -> dict[int, list[models.Miembro_Sucursal]]:
    '''
    Devuelvo un dict en la que cada clave es el id del usuario miembro y el
    valor es una lista con todos los objetos Miembro_Sucursal de ese usuario
    '''
    grupos = {}

    for m in miembros:
        if m.usuario_id not in grupos:
            grupos[m.usuario_id] = []
        
        grupos[m.usuario_id].append(m)

    return grupos

def miembros_empresa_out(
    miembros_empresa: list[models.Miembro_Empresa],
    miembros_sucursales: list[models.Miembro_Sucursal],
) -> schemas_empresa.MiembrosEmpresaOut:

    grupos = agrupar_miembros_por_usuario(miembros_sucursales)

    miembros_sucursales_out = [miembro_sucursal_out(lista) for lista in grupos.values()]

    miembros_emp_out = [miembro_empresa_out(m) for m in miembros_empresa]

    return schemas_empresa.MiembrosEmpresaOut(
        miembros_empresa=miembros_emp_out,
        miembros_sucursales=miembros_sucursales_out,
    )