from mappers.common import telefonos, direccion_out, disponibilidad_servicio, miembro_out
from core import auxiliares, timezone
from schemas import common as schemas_common
from schemas import empresa as schemas_empresa

# Convierte un objeto de la clase Empresa de SQLAlchemy en uno de clase EmpresaHomeOut de Pydantic
def empresa_home_out(empresa, miembro_rol):

    empresa_out = schemas_empresa.EmpresaHomeOut(
        id=empresa.id,
        nombre=empresa.nombre,
        logo_url=empresa.logo_url,
        rol=miembro_rol)

    return empresa_out

def sucursal_perfil_out(sucursal):

    out = schemas_empresa.SucursalPerfilOut(
        id=sucursal.id,
        nombre=sucursal.nombre,
        email=sucursal.email,
        reserva_publica_habilitada=sucursal.reserva_publica_habilitada,
        calificacion=sucursal.calificacion,
        telefonos=telefonos(sucursal.telefonos),
        direccion=direccion_out(sucursal.direccion),
    )

    return out

def empresa_perfil_out(empresa, miembro_rol):

    empresa_out = schemas_empresa.EmpresaPerfilOut(
        id=empresa.id,
        cuit=empresa.cuit,
        nombre=empresa.nombre,
        email=empresa.email,
        rubro=empresa.rubro,
        rubro2=empresa.rubro2,
        logo_url=empresa.logo_url,
        rol=miembro_rol,
        sucursales=[sucursal_perfil_out(sucursal) for sucursal in empresa.sucursales],
    )

    return empresa_out

def empresa_logo_out(logo_url):
    return schemas_empresa.EmpresaLogoOut(logo_url=logo_url)

def miembro_empresa_out(miembro):

    out = schemas_empresa.MiembroEmpresaOut(
        miembro=miembro_out(miembro),
        rol=auxiliares.transformar_rol(miembro.rol, contexto="empresa"), # string
    )

    return out

def sucursal_de_miembro(miembro):

    out = schemas_empresa.SucursalDeMiembro(
        id=miembro.sucursal.id,
        nombre=miembro.sucursal.nombre,
        rol=auxiliares.transformar_rol(miembro.rol, contexto="sucursal"), # string
    )

    return out

def miembro_sucursal_out(miembros):
    if not miembros: # innecesario pero por las dudas si después se modifica código, esto protege de que no explote
        raise ValueError("La función mappers_empresa.miembro_sucursal_out no puede recibir una lista vacía")

    # Tomamos un miembro cualquiera para obtener los datos del usuario
    primer_miembro = miembros[0]

    out = schemas_empresa.MiembroSucursalOut(
        miembro=miembro_out(primer_miembro),
        sucursales=[sucursal_de_miembro(m) for m in miembros]
    )

    return out

def agrupar_miembros_por_usuario(miembros):
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

def miembros_empresa_out(miembros_empresa: list, miembros_sucursales: list):

    grupos = agrupar_miembros_por_usuario(miembros_sucursales)

    miembros_sucursales_out = [miembro_sucursal_out(lista) for lista in grupos.values()]

    miembros_emp_out = [miembro_empresa_out(m) for m in miembros_empresa]

    return schemas_empresa.MiembrosEmpresaOut(
        miembros_empresa=miembros_emp_out,
        miembros_sucursales=miembros_sucursales_out
    )