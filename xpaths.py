"""
Catálogo de selectores Subcontrataley.

Prefijos:
  login.* / post_login.*  — autenticación
  nav.*                   — tronco común hasta Cargar plantillas
  plantilla.*             — elegir tipo de plantilla (rama)
  <flujo>.*               — pasos propios de cada carga
"""

LOGIN_URL = "https://www5.subcontrataley.cl/login.php"

# None = pendiente de captura (el flujo llega al tronco y avisa)
XPATHS = {
    # --- Login ---
    "login.usuario": "/html/body/div[1]/div[1]/div[2]/form/div[2]/div[1]/input",
    "login.password": "/html/body/div[1]/div[1]/div[2]/form/div[2]/div[2]/input",
    "login.boton_iniciar": "/html/body/div[1]/div[1]/div[2]/form/div[4]/button",
    # --- Post-login (modal INFORMACIÓN / avisos) ---
    # Preferir "Cancelar" por texto; el absolute path queda de respaldo
    "post_login.btn_cancelar": (
        "//*[self::button or self::a or self::span]"
        "[contains(normalize-space(.),'Cancelar') "
        "or contains(normalize-space(.),'Cerrar')]"
    ),
    "post_login.boton": "/html/body/div[13]/div[4]/div/div/div[3]/button",
    "post_login.btn_cerrar_x": (
        "//div[contains(@class,'modal')]"
        "//button[contains(@class,'close') or @data-dismiss='modal' "
        "or contains(@class,'btn-close') or @aria-label='Close']"
    ),
    # --- Tronco común → Cargar plantillas ---
    "nav.paso_1": "/html/body/div[6]/div[2]/div[2]/a",
    "nav.paso_2": "/html/body/div[6]/div[1]/div[1]/a[3]",
    "nav.cargar_plantillas": "/html/body/div[6]/div[2]/div[3]/div[1]",
    # --- Rama: elegir plantilla (otras ramas, pendiente) ---
    "plantilla.libro_asistencia": None,
    "plantilla.pagos_afp_afc": None,
    "plantilla.pagos_isapre_fonasa": None,
    # --- Liquidaciones de Sueldo ---
    "liquidaciones.select_tipo": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[2]/div[5]/select"
    ),
    "liquidaciones.select_periodo": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[2]/div[6]/select"
    ),
    "liquidaciones.btn_descargar_plantilla": "//*[@id='cmsd_btn_descargar_plantilla']",
    # Toggle entre tarjetas del form de carga masiva
    "liquidaciones.ir_a_descargar": "/html/body/div[6]/div[2]/div[3]/div[1]",
    # --- Liquidaciones: carga de plantilla + PDFs ---
    "liquidaciones.ir_a_cargar": "/html/body/div[6]/div[2]/div[3]/div[2]",
    "liquidaciones.input_excel": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[2]/div[1]/div/div/div[1]/div/div[1]/input"
    ),
    "liquidaciones.btn_enviar_excel": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[2]/div[1]/div/div/div[1]/div/div[2]/button"
    ),
    "liquidaciones.zona_upload_liquidaciones": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[2]/div[1]/div/div/div[3]/div[2]"
    ),
    # Dropzone documentos (asistencia / carga 1-doc). Confirmado en UI 2026-08-03.
    "asistencias.zona_upload_documentos": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[2]/div[1]/div/div/div[3]/div[2]"
    ),
    # Mensaje interno del dropzone (opcional; el input real es .dz-hidden-input)
    "asistencias.zona_upload_documentos_msg": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[2]/div[1]/div/div/div[3]/div[2]/div[1]"
    ),
    "liquidaciones.zona_upload_transferencias": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[3]/div/div/div/div/div/div"
    ),
    "liquidaciones.btn_confirmar_carga": (
        "/html/body/div[6]/div[2]/div[3]/div[3]/div[2]/div[1]/div/div/div[4]/button"
    ),
    # Alias explícito (mismo botón; id del portal)
    "liquidaciones.btn_validar_documentos": (
        "//*[@id='cmsd_btn_validar_documentos']"
    ),
    # Pantalla 2.3 tras validar OK (0 errores)
    "asistencias.btn_realizar_carga_masiva": (
        "//button[contains(normalize-space(.),'Realizar Carga Masiva')]"
    ),
    # Tras "Realizar Carga Masiva": SOLO cuando el proceso ya terminó de cargar.
    # No clickear de inmediato; espera éxito/fin de carga y luego este botón.
    "liquidaciones.btn_post_confirmar": (
        "/html/body/div[6]/div[2]/div[2]/div[1]/div/div/div/div/div/div/div[5]/div[2]/button/span"
    ),
    # Alias libro de asistencia / misma pantalla post-carga masiva
    "asistencias.btn_despues_carga_masiva": (
        "/html/body/div[6]/div[2]/div[2]/div[1]/div/div/div/div/div/div/div[5]/div[2]/button/span"
    ),
    # --- Listado trabajadores (menú finiquitos / personal) ---
    # Tras Carga Masiva (nav.paso_1).
    "trabajadores.paso_1": (
        "//*[self::a or self::div or self::button or self::span]"
        "[contains(normalize-space(.),'Finiquitar trabajadores')]"
    ),
    # "Descarga Plantilla Nueva" en GESTIÓN DE DESVINCULACIÓN…
    "trabajadores.paso_2": "/html/body/div[6]/div[2]/div[3]/div[1]",
    # Botón que dispara la descarga del Excel de trabajadores activos
    "trabajadores.btn_exportar": (
        "/html/body/div[6]/div[2]/div[4]/div/div[2]/div[6]/button"
    ),
    # --- Ingreso trabajadores (Crear trabajadores → Subir plantilla) ---
    # Sidebar <a> con onclick (el contains genérico matchea <html> y el click
    # cae en el centro → card Finiquitar).
    "ingreso.crear_trabajadores": (
        "//a[contains(@class,'menu-left-item')]"
        "[contains(normalize-space(.),'Crear trabajadores')]"
    ),
    # Card derecha en CREAR TRABAJADORES (texto distinto a Finiquitar)
    "ingreso.subir_plantilla": (
        "//div[contains(@class,'col-5')]"
        "[contains(normalize-space(.),'Subir Plantilla')]"
        "[not(contains(normalize-space(.),'Descargar'))]"
    ),
    # Dropzone Crear (estructura distinta a Finiquitar; id portal cmt_*)
    "ingreso.input_excel": (
        "//div[contains(@class,'dropzone') and contains(@class,'dz-clickable')]"
    ),
    # Botón verde Validar Plantilla
    "ingreso.btn_enviar": "//*[@id='cmt_btn_validar_planilla']",
    # Card izquierda: Descargar Nueva Plantilla
    "ingreso.descargar_plantilla": (
        "//div[contains(@class,'col-5')]"
        "[contains(normalize-space(.),'Descargar Nueva Plantilla')]"
    ),
    # Botón verde Descargar Plantilla (plantilla vacía fresca)
    "ingreso.btn_descargar_plantilla": "//*[@id='cmt_btn_descargar_plantilla']",
    # Tras validación OK (0 errores)
    "ingreso.btn_realizar_carga_masiva": "//*[@id='cmt_btn_realizar_carga_masiva']",
}


def xp(key: str) -> str:
    """Obtiene un XPath por clave. Falla claro si falta o está pendiente."""
    if key not in XPATHS:
        raise KeyError(
            f"XPath no definido: '{key}'. Agrégalo en xpaths.py tras capturarlo."
        )
    value = XPATHS[key]
    if not value:
        raise KeyError(
            f"XPath pendiente de captura: '{key}'. "
            "Pásalo en el chat y lo cableamos."
        )
    return value


def xpath_pendiente(key: str) -> bool:
    return key in XPATHS and not XPATHS[key]
