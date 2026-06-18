const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, Header, Footer, TableOfContents, PageBreak
} = require("docx");

const GOLD = "B8860B", DARK = "15192A", RED = "B00020", AMBER = "B8860B",
      GREEN = "2E7D32", GREY = "555555", BLUE = "1F4E79";
const CW = 9360;

const P = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 120, before: opts.before ?? 0, line: 276 },
  alignment: opts.align,
  children: [new TextRun({ text, bold: opts.bold, italics: opts.italics,
    color: opts.color, size: opts.size, font: "Arial" })]
});
const runs = (arr, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 120, before: opts.before ?? 0, line: 276 },
  children: arr.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i,
    color: r.c, font: r.mono ? "Consolas" : "Arial", size: r.size ?? 22 }))
});
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: "Arial" })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: "Arial" })] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, font: "Arial" })] });
const bullet = (t, lvl = 0) => new Paragraph({
  numbering: { reference: "bullets", level: lvl },
  spacing: { after: 80, line: 268 },
  children: Array.isArray(t) ? t.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i, color: r.c, font: r.mono ? "Consolas" : "Arial", size: 22 }))
                              : [new TextRun({ text: t, font: "Arial", size: 22 })]
});
const num = (t) => new Paragraph({ numbering: { reference: "nums", level: 0 },
  spacing: { after: 80, line: 268 }, children: [new TextRun({ text: t, font: "Arial", size: 22 })] });
const spacer = () => new Paragraph({ children: [], spacing: { after: 60 } });

function codeBlock(lines) {
  return new Paragraph({
    shading: { fill: "F4F4F4", type: ShadingType.CLEAR },
    spacing: { after: 140, before: 40, line: 240 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: GOLD, space: 6 } },
    children: lines.flatMap((l, i) => {
      const r = [new TextRun({ text: l, font: "Consolas", size: 18, color: "333333" })];
      if (i < lines.length - 1) r.push(new TextRun({ break: 1 }));
      return r;
    })
  });
}

function cell(text, { w, fill, bold, color, align, size } = {}) {
  const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
  const content = Array.isArray(text)
    ? text.map(line => new Paragraph({ alignment: align, spacing: { after: 30, line: 252 },
        children: [new TextRun({ text: line.t ?? line, bold: line.b ?? bold, italics: line.i, color: line.c ?? color, font: line.mono ? "Consolas" : "Arial", size: line.size ?? size ?? 19 })] }))
    : [new Paragraph({ alignment: align, spacing: { after: 0, line: 252 },
        children: [new TextRun({ text, bold, color, font: "Arial", size: size ?? 19 })] })];
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: fill ? { fill, type: ShadingType.CLEAR } : undefined,
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    borders: { top: border, bottom: border, left: border, right: border },
    children: content
  });
}

function table(widths, headers, rows, headFill = DARK) {
  const headRow = new TableRow({ tableHeader: true, children:
    headers.map((h, i) => cell(h, { w: widths[i], fill: headFill, bold: true, color: "FFFFFF", size: 19 })) });
  const bodyRows = rows.map((r, ri) => new TableRow({ children:
    r.map((c, i) => {
      const isObj = c && typeof c === "object" && !Array.isArray(c);
      const txt = isObj ? c.t : c;
      return cell(txt, { w: widths[i], fill: isObj && c.fill ? c.fill : (ri % 2 ? "FAFAFA" : undefined),
        bold: isObj ? c.b : false, color: isObj ? c.c : undefined, align: isObj ? c.align : undefined });
    }) }));
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: widths, rows: [headRow, ...bodyRows] });
}

const tag = (sev) => {
  const map = { "CRÍTICO": RED, "IMPORTANTE": AMBER, "DESEABLE": GREEN, "OK": GREEN };
  return { t: sev, b: true, c: "FFFFFF", fill: map[sev], align: AlignmentType.CENTER };
};

const children = [];

children.push(
  new Paragraph({ spacing: { before: 2200, after: 0 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "FretMind", bold: true, size: 64, color: DARK, font: "Arial" })] }),
  new Paragraph({ spacing: { after: 40 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Tutor inteligente de guitarra acústica", italics: true, size: 26, color: GREY, font: "Arial" })] }),
  new Paragraph({ spacing: { before: 480, after: 0 }, alignment: AlignmentType.CENTER,
    border: { top: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 8 }, bottom: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 8 } },
    children: [new TextRun({ text: "AUDITORÍA TÉCNICA DE ARQUITECTURA", bold: true, size: 36, color: GOLD, font: "Arial" })] }),
  new Paragraph({ spacing: { before: 600 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Backend FastAPI (Python)  +  App Android (Kotlin / Jetpack Compose)", size: 24, color: DARK, font: "Arial" })] }),
  new Paragraph({ spacing: { before: 1400 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Proyecto de tesis — Ingeniería en Sistemas", size: 22, color: GREY, font: "Arial" })] }),
  new Paragraph({ spacing: { before: 120 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Autor del proyecto: Alejandro Guzmán", size: 22, color: GREY, font: "Arial" })] }),
  new Paragraph({ spacing: { before: 120 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Fecha del informe: 18 de junio de 2026", size: 22, color: GREY, font: "Arial" })] }),
  new Paragraph({ spacing: { before: 120 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Alcance: solo análisis — no se modificó código", size: 20, italics: true, color: GREY, font: "Arial" })] }),
  new Paragraph({ children: [new PageBreak()] })
);

children.push(H1("Tabla de contenidos"));
children.push(new TableOfContents("Tabla de contenidos", { hyperlink: true, headingStyleRange: "1-2" }));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("1. Resumen ejecutivo"));
children.push(P("Esta auditoría evalúa el estado de FretMind, compuesto por un backend REST en FastAPI (Python) y una aplicación Android en Kotlin con Jetpack Compose. El backend implementa un afinador con un pipeline DSP completo, un tutor por reglas (Wilfredo) y análisis de práctica. La app está estructurada en capas (UI Compose, ViewModels, Repositorios, servicios Retrofit y DTOs)."));
children.push(P("El proyecto muestra una intención arquitectónica sólida y un backend de procesamiento de señal notablemente completo. Sin embargo, la auditoría detecta una brecha estructural central: la capa de red de la app (DTOs, Retrofit, repositorios y ViewModels) está construida pero ninguna pantalla la consume; todas las pantallas trabajan con datos simulados (hardcodeados). En la práctica, la app y el backend hoy no están conectados de extremo a extremo."));
children.push(P("A esto se suman varios bloqueos para los objetivos de tesis: no existe persistencia (los perfiles viven en un diccionario en memoria), el login con Google es un stub, no hay captura de audio ni permiso de micrófono en la app, y el sistema adaptativo tiene un bug que impide guardar la consistencia. El endpoint principal de práctica (POST /practica) está roto y lanzaría una excepción en tiempo de ejecución."));
children.push(spacer());
children.push(H3("Panorama de hallazgos por severidad"));
children.push(table([2600, 1400, 5360],
  ["Severidad", "N.º", "Foco principal"],
  [
    [tag("CRÍTICO"), { t: "6", align: AlignmentType.CENTER, b: true }, "UI desconectada, /practica roto, bug adaptativo, sin persistencia, login Google stub, sin captura de audio"],
    [tag("IMPORTANTE"), { t: "8", align: AlignmentType.CENTER, b: true }, "Endpoints sin cliente, pantallas huérfanas, búsqueda no conectada, CORS, contrato de respuesta inconsistente"],
    [tag("DESEABLE"), { t: "7", align: AlignmentType.CENTER, b: true }, "Nomenclatura, dependencias muertas, ausencia de tests/CI, README desactualizado, logging"],
  ]));
children.push(spacer());
children.push(runs([{ t: "Veredicto: ", b: true }, { t: "el proyecto es una base de prototipo con piezas de alta calidad (pipeline DSP, diseño de DTOs), pero hoy no funciona de extremo a extremo. Antes de avanzar hacia MongoDB, perfil y prácticas tipo Yousician, se requiere una fase de estabilización que conecte la UI con el backend y repare los bloqueos críticos." }]));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("2. Metodología y arquitectura actual"));
children.push(H2("2.1 Metodología de auditoría"));
children.push(P("Se realizó una revisión estática del repositorio, sin ejecutar el sistema y sin modificar código. Se inspeccionaron: los routers y servicios FastAPI, el modelo de dominio e IA adaptativa, la capa Retrofit/DTOs de Android, repositorios, ViewModels, pantallas Compose, el grafo de navegación, el manifiesto, las dependencias Gradle y la configuración del cliente HTTP. El contraste endpoint contra DTO se hizo campo por campo, considerando la política de nombres de Gson."));
children.push(H2("2.2 Vista de arquitectura"));
children.push(codeBlock([
  "ANDROID (Kotlin + Jetpack Compose)                BACKEND (FastAPI)",
  "------------------------------------              ----------------------------",
  "Screens (Compose)   <-- [DESCONECTADO] -->  ViewModels (UiState)",
  "                                                  |",
  "                                            Repositories",
  "                                                  |",
  "                                            FastApiService (Retrofit)  --HTTP-->  routers:",
  "                                            SongsterrService           --HTTP-->    /tuner/*",
  "                                                                                     /wilfredo/*",
  "                                                                                     /practica*",
  "                                            ApiClient (10.0.2.2:8000)              services + audio DSP",
  "                                                                                   modelo_adaptativo (in-memory)",
]));
children.push(runs([{ t: "Lectura clave del diagrama: ", b: true }, { t: "la frontera entre Screens y ViewModels está rota. Todo lo que está debajo de los ViewModels es técnicamente correcto pero queda inalcanzable porque ninguna pantalla invoca un ViewModel." }]));
children.push(H2("2.3 Inventario de endpoints del backend"));
children.push(table([3400, 1100, 4860],
  ["Endpoint", "Método", "Estado"],
  [
    ["/practica", "POST", { t: "ROTO (analyze_file inexistente)", c: RED, b: true }],
    ["/practica/analyze", "POST", "Funcional"],
    ["/tuner/pitch", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/verify", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/identify", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/pitch/file", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/chord/file", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/analyze", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/analyze/file", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/analyze/raw", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/calibrate", "POST", "Funcional · consumido (DTO)"],
    ["/tuner/pipeline", "GET", "Funcional · consumido (DTO)"],
    ["/tuner/validate", "POST", { t: "Sin cliente Retrofit", c: AMBER, b: true }],
    ["/tuner/pipeline/compare", "POST", { t: "Sin cliente Retrofit", c: AMBER, b: true }],
    ["/tuner/quality", "POST", { t: "Sin cliente Retrofit", c: AMBER, b: true }],
    ["/wilfredo/chat", "POST", "Funcional · consumido (DTO)"],
    ["/wilfredo/analyze", "POST", "Funcional · consumido (DTO)"],
    ["/wilfredo/plan", "POST", { t: "Con DTO, sin uso en ViewModel", c: AMBER }],
    ["/wilfredo/tuner", "POST", "Funcional · consumido (DTO)"],
    ["/wilfredo/chord", "POST", "Funcional · consumido (DTO)"],
  ]));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("3. Objetivo 1 — Coincidencia endpoints FastAPI con DTOs Kotlin"));
children.push(P("El cliente Retrofit configura Gson con FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES, de modo que los campos Kotlin en camelCase (p. ej. notaEsperada, freqTeorica, framesAnalizados) se serializan y deserializan como snake_case (nota_esperada, freq_teorica, frames_analizados), que es justo lo que produce y espera el backend. Con esa política, los DTOs de los endpoints efectivamente declarados coinciden a nivel de estructura."));
children.push(runs([{ t: "Conclusión del Objetivo 1: ", b: true }, { t: "la coincidencia es ~95% a nivel de contrato declarado, NO 100%. Hay un caso bien resuelto (" }, { t: "hay_señal", mono: true }, { t: " con " }, { t: "@SerializedName", mono: true }, { t: " por la ñ) y tres desajustes reales descritos abajo." }]));
children.push(spacer());
children.push(table([2700, 3000, 3660],
  ["Área", "Resultado", "Observación"],
  [
    ["Tuner (pitch/verify/identify/analyze/file/raw/calibrate/pipeline)", { t: "Coincide", c: GREEN, b: true }, "Campos alineados vía política snake_case; hay_señal protegido con @SerializedName(\"hay_señal\")."],
    ["Wilfredo (chat/analyze/plan/tuner/chord)", { t: "Coincide", c: GREEN, b: true }, "Requests y data classes consistentes con los modelos Pydantic."],
    ["PracticaResult.profile", { t: "Desajuste de datos", c: RED, b: true }, "El DTO espera consistencia_avg, pero el modelo adaptativo nunca lo actualiza (bug consistency_avg). Siempre llegaría 0.0."],
    ["Wrapper de respuesta", { t: "Inconsistente", c: AMBER, b: true }, "/tuner/* y /wilfredo/* devuelven {success,data}; /practica y /practica/analyze devuelven el objeto plano sin envoltorio."],
    ["/practica (resultado)", { t: "No verificable", c: RED, b: true }, "El endpoint está roto en runtime, por lo que su contrato real nunca se materializa."],
  ]));
children.push(spacer());
children.push(H3("Detalle: el wrapper genérico"));
children.push(codeBlock([
  "// Kotlin: data class ApiResponse<T>(success, data, error)",
  "// Tuner/Wilfredo ->  { \"success\": true, \"data\": { ... } }   OK con ApiResponse<T>",
  "// Practica       ->  { \"metrics\": {...}, \"profile\": {...} }  SIN wrapper -> Response<PracticaResult>",
]));
children.push(P("La app contempla ambos formatos (los métodos de práctica no usan ApiResponse), por lo que compila; pero el contrato del API no es uniforme. Para tesis conviene estandarizar un único envoltorio de respuesta en todos los endpoints."));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("4. Objetivo 2 — Endpoints sin consumir"));
children.push(P("Existen dos niveles de no consumo. El primero es a nivel de capa de red (endpoints sin método Retrofit). El segundo, más grave, es que aunque el método exista, ninguna pantalla lo dispara (ver Objetivo 3)."));
children.push(H2("4.1 Endpoints sin cliente Retrofit"));
children.push(bullet([{ t: "/tuner/validate", mono: true }, { t: " — valida si el audio corresponde a una nota de guitarra (template matching armónico). No tiene DTO ni método en FastApiService." }]));
children.push(bullet([{ t: "/tuner/pipeline/compare", mono: true }, { t: " — compara la señal antes/después del pipeline DSP (SNR, confianza). Sin cliente." }]));
children.push(bullet([{ t: "/tuner/quality", mono: true }, { t: " — diagnostica clipping, silencio y SNR con recomendaciones. Sin cliente." }]));
children.push(P("Nota para tesis: estos tres endpoints son precisamente los que generan evidencia experimental cuantitativa (mejora del pipeline, capacidad de discriminar señal de guitarra, calidad de grabación). Hoy se desperdician; deberían exponerse y usarse en el capítulo de resultados."));
children.push(H2("4.2 Endpoints con cliente pero sin uso desde la UI"));
children.push(bullet([{ t: "/wilfredo/plan", mono: true }, { t: " — existe el método (wilfredoPlan) y el repositorio (getPracticePlan), pero ningún ViewModel lo llama." }]));
children.push(bullet([{ t: "Songsterr /api/songs", mono: true }, { t: " — SearchRepository y SearchViewModel lo invocan, pero SearchScreen usa una lista de canciones hardcodeada y nunca llama al ViewModel." }]));
children.push(bullet("Todos los endpoints de tuner/wilfredo/practica — tienen repositorio y ViewModel, pero como ninguna pantalla instancia esos ViewModels, en la práctica el 100% de los endpoints queda sin disparar desde la app en ejecución."));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("5. Objetivo 3 — Pantallas sin conectar"));
children.push(H2("5.1 Hallazgo central: ninguna pantalla usa su ViewModel"));
children.push(P("Una búsqueda sobre el paquete ui/screens no encuentra una sola referencia a viewModel() ni a ViewModel. Las pantallas mantienen su estado con remember/mutableStateOf y datos de ejemplo. Es decir: la cadena Screen → ViewModel → Repository → API existe en el código pero está cortada en el primer eslabón."));
children.push(table([2400, 3200, 3760],
  ["Pantalla", "ViewModel disponible", "Estado real"],
  [
    ["HomeScreen", "HomeViewModel", { t: "No lo usa — UI estática", c: RED }],
    ["SearchScreen", "SearchViewModel", { t: "No lo usa — canciones hardcodeadas", c: RED }],
    ["PracticeScreen", "PracticeViewModel", { t: "No lo usa — flujo local simulado", c: RED }],
    ["TunerScreen", "TunerViewModel", { t: "No lo usa — sin red ni micrófono", c: RED }],
    ["ProgressScreen", "ProgressViewModel", { t: "No lo usa — datos ficticios", c: RED }],
    ["ChatScreen", "ChatViewModel", { t: "No lo usa — sin llamadas a Wilfredo", c: RED }],
    ["LoginScreen", "LoginViewModel", { t: "No lo usa — solo navega", c: RED }],
  ]));
children.push(H2("5.2 Pantallas huérfanas (no registradas en navegación)"));
children.push(bullet([{ t: "ProfileScreen", b: true }, { t: " — no tiene ruta en el NavHost ni destino en Dest. El Perfil de usuario (objetivo de tesis) hoy es inaccesible y muestra datos fijos (Usuario: José)." }]));
children.push(bullet([{ t: "SplashScreen", b: true }, { t: " — recibe un NavController y navega a la ruta splash, que no existe; además el startDestination es Login, por lo que el splash nunca se muestra." }]));
children.push(bullet([{ t: "WilfredoScreen", b: true }, { t: " (archivo Wilfredoscreen.kt) — duplica la función del chat pero no se registra; la ruta wilfredo usa ChatScreen. Botón Enviar con onClick vacío." }]));
children.push(P("Conviene decidir una única pantalla de chat y un único punto de entrada, eliminar duplicados y dar ruta al Perfil."));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("6. Objetivo 4 — Riesgos para la integración con MongoDB"));
children.push(P("Hoy no existe ninguna capa de datos: no hay MongoDB, ni ningún otro motor, ni ORM/ODM. El estado del usuario se guarda en un diccionario global en memoria dentro de main.py:"));
children.push(codeBlock([
  "profiles = {}                       # main.py  (se pierde al reiniciar)",
  "if user_id not in profiles:",
  "    profiles[user_id] = UserProfile()",
]));
children.push(table([3200, 1500, 4660],
  ["Riesgo", "Severidad", "Detalle / mitigación"],
  [
    ["Sin capa de persistencia", tag("CRÍTICO"), "Estado en RAM: se pierde al reiniciar y no es compartible entre procesos/workers de Uvicorn. Introducir una capa Repository en el backend antes de migrar."],
    ["Identidad de usuario sin definir", tag("CRÍTICO"), "user_id llega como string arbitrario por query param, sin autenticación. MongoDB necesita una clave estable (sub de Google / _id). Resolver junto con Login Google."],
    ["Modelo de dominio anémico", tag("IMPORTANTE"), "UserProfile solo tiene 4 floats; falta historial de sesiones, timestamps, ejercicios. Diseñar esquema antes de crear colecciones."],
    ["Bug que corrompería datos", tag("IMPORTANTE"), "consistency_avg vs consistencia_avg: persistir hoy guardaría consistencia siempre en 0. Corregir antes de escribir en Mongo."],
    ["Sin configuración/secretos", tag("IMPORTANTE"), "No hay variables de entorno ni gestión de la URI de conexión. Añadir .env / settings y NO commitear credenciales."],
    ["Concurrencia y async", tag("DESEABLE"), "FastAPI es async; usar un driver async (Motor) o un ODM (Beanie) para no bloquear el event loop."],
    ["Serialización Pydantic con Mongo", tag("DESEABLE"), "Mapear _id/ObjectId y fechas a los DTOs; definir modelos Pydantic de salida explícitos para no filtrar campos internos."],
  ]));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("7. Objetivo 5 — Deuda técnica"));
children.push(H2("7.1 Funcional / correctitud"));
children.push(bullet([{ t: "POST /practica está roto: ", b: true }, { t: "main.py llama analyzer.analyze_file(), método inexistente en SignalAnalyzer (solo expone load_audio, detect_pitch, rms_energy, spectral_centroid, tempo). Lanzaría AttributeError (HTTP 500)." }]));
children.push(bullet([{ t: "Bug del modelo adaptativo: ", b: true }, { t: "update() escribe profile.consistency_avg mientras el dataclass define consistencia_avg; se crea un atributo fantasma y la consistencia real nunca se actualiza." }]));
children.push(bullet([{ t: "ProgressRepository hace un hack: ", b: true }, { t: "para leer progreso crea un WAV de 1KB de ceros y lo envía a POST /practica (que además está roto). Una lectura no debería subir audio ni reutilizar el endpoint de escritura." }]));
children.push(bullet([{ t: "Reinterpretación arbitraria de métricas: ", b: true }, { t: "en Home/Progress se calcula streak = precision*10, accuracy = consistencia*100, sessions = error*5, sin sentido semántico." }]));
children.push(H2("7.2 Seguridad y configuración"));
children.push(bullet([{ t: "CORS inseguro: ", b: true }, { t: "allow_origins=[\"*\"] junto con allow_credentials=True es una combinación inválida que los navegadores rechazan y una mala práctica de seguridad." }]));
children.push(bullet("Errores devueltos como HTTP 200 con {success:false}: no se usan códigos de estado correctos; HTTPException se importa pero no se usa. Dificulta el manejo de errores y el testing."));
children.push(bullet("Dependencias muertas / contradictorias: el entorno tiene instalados openai, google-genai y google-generativeai, no listados en requirements.txt y en contradicción con el lema sin APIs externas. Limpiar."));
children.push(H2("7.3 Estructura, estilo y proceso"));
children.push(bullet("Nomenclatura inconsistente: clase modelo_adaptativo en snake_case (no PEP8); carpeta analizador_señales con ñ y android app con espacio (fricción con herramientas y rutas); mezcla español/inglés."));
children.push(bullet("Identidad de app placeholder: applicationId/namespace com.example.prueba; el nombre oscila entre FretMind, Prueba y prueba."));
children.push(bullet("Sin pruebas automatizadas ni CI: solo test_microfono.py y tester.py manuales."));
children.push(bullet("README desactualizado: documenta /tuner/chord (no existe; lo correcto es /tuner/identify) y ejemplos con precision=80, cuando el modelo Pydantic exige 0.0–1.0 (ge=0, le=1); esos ejemplos fallarían validación."));
children.push(bullet("Logging por print a server.log, sin logging estructurado ni niveles."));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("8. Clasificación consolidada de hallazgos"));
children.push(H2("8.1 Críticos (bloquean el avance)"));
children.push(table([900, 4200, 4260],
  ["ID", "Hallazgo", "Impacto"],
  [
    ["C1", "La UI no consume la capa de red (ninguna pantalla usa ViewModels)", "App y backend desconectados de extremo a extremo"],
    ["C2", "POST /practica roto (analyze_file inexistente)", "El flujo de práctica/perfil falla en runtime (500)"],
    ["C3", "Bug consistency_avg en el modelo adaptativo", "La consistencia nunca se persiste; adaptación inválida"],
    ["C4", "Sin persistencia (perfiles en memoria)", "Datos efímeros; bloquea MongoDB/Perfil/adaptativo"],
    ["C5", "Login Google es un stub", "Sin identidad real de usuario ni seguridad"],
    ["C6", "Sin captura de audio ni permiso RECORD_AUDIO", "Afinador y prácticas en vivo imposibles"],
  ]));
children.push(H2("8.2 Importantes (afectan calidad e integración)"));
children.push(table([900, 4200, 4260],
  ["ID", "Hallazgo", "Impacto"],
  [
    ["I1", "Endpoints /tuner/validate, /pipeline/compare, /quality sin cliente", "Se pierde evidencia experimental valiosa"],
    ["I2", "/wilfredo/plan con repo pero sin uso", "Funcionalidad de plan no llega al usuario"],
    ["I3", "ProgressRepository envía audio falso para leer progreso", "Diseño incorrecto y frágil"],
    ["I4", "CORS '*' + allow_credentials=True", "Configuración inválida e insegura"],
    ["I5", "Pantallas huérfanas (Profile, Splash, Wilfredo)", "Perfil inaccesible; código duplicado/muerto"],
    ["I6", "Búsqueda no conectada + API Songsterr no oficial", "Resultados ficticios; dependencia frágil"],
    ["I7", "Contrato de respuesta inconsistente (wrapper)", "API no uniforme; parsing dispar"],
    ["I8", "Manejo de archivo temporal no seguro en /practica", "Colisiones de nombre, fugas si falla"],
  ]));
children.push(H2("8.3 Deseables (pulido y mantenibilidad)"));
children.push(table([900, 4200, 4260],
  ["ID", "Hallazgo", "Impacto"],
  [
    ["D1", "Dependencias muertas (openai/google-genai)", "Confusión y peso innecesario"],
    ["D2", "Nomenclatura/PEP8 y rutas con espacio/ñ", "Fricción de herramientas y lectura"],
    ["D3", "Sin tests automatizados ni CI", "Riesgo de regresiones"],
    ["D4", "Errores como HTTP 200; sin logging estructurado", "Observabilidad y manejo de errores pobres"],
    ["D5", "Identidad de app placeholder (com.example.prueba)", "No apto para publicación"],
    ["D6", "README desactualizado (endpoints/escala)", "Onboarding engañoso"],
    ["D7", "Política Gson frágil con caracteres no ASCII", "Mitigado con @SerializedName; documentar"],
  ]));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("9. Roadmap hacia los objetivos"));
children.push(P("El roadmap se ordena por dependencias: cada fase habilita la siguiente. La Fase 0 es prerrequisito de todo lo demás, porque sin conectar UI con backend y reparar los bloqueos, las funciones nuevas se construirían sobre cimientos rotos."));

children.push(H2("Fase 0 — Estabilización (prerrequisito)"));
children.push(num("Reparar POST /practica: usar un método real de análisis (p. ej. audio_processor.analyze_file o componer métodos de SignalAnalyzer) y devolver precision/consistencia/error coherentes."));
children.push(num("Corregir el bug consistency_avg → consistencia_avg en modelo_adaptativo."));
children.push(num("Conectar UNA pantalla a su ViewModel como patrón de referencia (recomendado: TunerScreen o ChatScreen) e ir replicando."));
children.push(num("Unificar el contrato de respuesta (envoltorio success/data/error en todos los endpoints)."));
children.push(num("Añadir permiso RECORD_AUDIO y restringir CORS a orígenes conocidos."));

children.push(H2("Fase 1 — Login con Google"));
children.push(bullet("App: integrar Credential Manager + Google Identity (las dependencias androidx.credentials y play-services-auth ya están en el build.gradle) para obtener el idToken real en LoginScreen vía LoginViewModel."));
children.push(bullet("Backend: endpoint /auth/google que verifique el idToken con google-auth (ya instalado), cree o recupere el usuario y emita un JWT propio."));
children.push(bullet("App: AuthRepository real + persistencia del token con DataStore (dependencia ya presente); enviar el JWT en las cabeceras vía interceptor OkHttp."));

children.push(H2("Fase 2 — MongoDB"));
children.push(bullet("Añadir driver async Motor (o el ODM Beanie) y configuración de URI por variables de entorno."));
children.push(bullet("Colecciones sugeridas: users (perfil + sub de Google), practice_sessions (histórico con timestamp), metrics/profile (estado adaptativo)."));
children.push(bullet("Introducir una capa Repository en el backend y reemplazar el dict profiles; indexar por user_id; modelos Pydantic de entrada y salida explícitos."));

children.push(H2("Fase 3 — Perfil de usuario"));
children.push(bullet("Dar ruta a ProfileScreen en el NavHost y un destino en Dest; conectarla a un ProfileViewModel."));
children.push(bullet("Endpoints GET /users/me y PUT /users/me; mostrar nombre, nivel, foto y métricas persistidas (no datos fijos)."));
children.push(bullet("Eliminar pantallas duplicadas/huérfanas (unificar chat; quitar o cablear Splash)."));

children.push(H2("Fase 4 — Sistema adaptativo"));
children.push(bullet("Sobre UserProfile persistido y corregido: guardar historial de sesiones y ajustar dificultad/recomendaciones según precision, consistencia y error."));
children.push(bullet("Endpoint de recomendación de ejercicios basado en el perfil; alimentar Home/Progress con datos reales en lugar de los cálculos arbitrarios actuales."));
children.push(bullet("Versionar el algoritmo (alpha del promedio exponencial) para poder comparar variantes en la tesis."));

children.push(H2("Fase 5 — Prácticas tipo Yousician"));
children.push(bullet("Captura de audio en tiempo real con AudioRecord; pipeline de baja latencia."));
children.push(bullet("Detección nota a nota: aprovechar /tuner/analyze/raw (frame a frame) o realizar detección on-device para minimizar latencia; considerar WebSocket para streaming."));
children.push(bullet("Sincronización con tablatura/partitura y scoring por nota/tiempo; feedback visual en vivo."));
children.push(bullet("Usar /tuner/validate y /tuner/quality para filtrar señal y guiar al usuario sobre la calidad de grabación."));
children.push(spacer());
children.push(H3("Resumen del roadmap"));
children.push(table([1500, 3500, 4360],
  ["Fase", "Objetivo", "Dependencias / habilitadores"],
  [
    [{ t: "0", b: true, align: AlignmentType.CENTER }, "Estabilización", "Prerrequisito de todo"],
    [{ t: "1", b: true, align: AlignmentType.CENTER }, "Login Google", "Fase 0; deps de credenciales ya presentes"],
    [{ t: "2", b: true, align: AlignmentType.CENTER }, "MongoDB", "Identidad de usuario (Fase 1)"],
    [{ t: "3", b: true, align: AlignmentType.CENTER }, "Perfil de usuario", "Persistencia (Fase 2)"],
    [{ t: "4", b: true, align: AlignmentType.CENTER }, "Sistema adaptativo", "Perfil persistido (Fase 3)"],
    [{ t: "5", b: true, align: AlignmentType.CENTER }, "Prácticas tipo Yousician", "Audio en vivo + adaptativo (Fases 0,4)"],
  ]));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("10. Recomendaciones para la tesis universitaria"));
children.push(H2("10.1 Aprovechar lo que ya es fuerte"));
children.push(P("El backend de procesamiento de señal es el mayor activo académico del proyecto. Los endpoints /tuner/pipeline, /tuner/pipeline/compare, /tuner/validate y /tuner/quality permiten medir y demostrar cuantitativamente la efectividad del preprocesamiento (SNR antes y después, confianza, discriminación de señal de guitarra). Recomendado dedicar un capítulo de resultados a estos experimentos, con gráficas comparativas."));
children.push(H2("10.2 Encuadre honesto del alcance"));
children.push(bullet("Documentar el estado real (prototipo con UI desconectada) y presentar la conexión UI con backend como parte del trabajo realizado, no como algo ya resuelto."));
children.push(bullet("Declarar explícitamente las limitaciones (sin persistencia inicial, login stub, sin audio en vivo) y cómo el roadmap las aborda: esto fortalece la sección de trabajo futuro y la madurez del análisis."));
children.push(H2("10.3 Rigor de ingeniería defendible"));
children.push(bullet("Incluir diagramas C4 (contexto, contenedores, componentes) y un diagrama de secuencia de un caso de uso completo (p. ej. afinar una cuerda) para evidenciar comprensión arquitectónica."));
children.push(bullet("Añadir un mínimo de pruebas automatizadas (pytest para servicios DSP y de reglas; tests de ViewModel o de instrumentación en Android) y mencionarlas como evidencia de calidad."));
children.push(bullet("Justificar decisiones: por qué reglas en lugar de IA externa, por qué MongoDB frente a SQL, por qué promedio exponencial para la adaptación (y sus límites)."));
children.push(H2("10.4 Métrica de evaluación del adaptativo"));
children.push(P("Para sustentar el sistema adaptativo, definir métricas objetivas: evolución de precision/consistencia a lo largo de sesiones simuladas (el simulador ya existe en ia/simulador.py) y, si es posible, un pequeño estudio con usuarios. Comparar al menos dos valores de alpha para mostrar el efecto del suavizado."));
children.push(spacer());
children.push(runs([{ t: "Cierre. ", b: true }, { t: "FretMind tiene una base técnica valiosa y una arquitectura bien intencionada. El trabajo más urgente no es agregar funciones, sino cerrar la brecha UI con backend y reparar los bloqueos críticos. Hecho eso, el roadmap por fases conduce de forma ordenada a Login Google, MongoDB, Perfil, sistema adaptativo y prácticas en tiempo real, con material experimental ya disponible para respaldar la tesis." }]));

const doc = new Document({
  creator: "Auditoría técnica",
  title: "FretMind — Auditoría técnica de arquitectura",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial", color: DARK },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: "333333" },
        paragraph: { spacing: { before: 140, after: 80 }, outlineLevel: 2 } },
    ]
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 280 } } } }] },
    { reference: "nums", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 280 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "DDDDDD", space: 4 } },
      children: [new TextRun({ text: "FretMind · Auditoría técnica de arquitectura", size: 16, color: "999999", font: "Arial" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Página ", size: 16, color: "999999", font: "Arial" }),
                new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "999999", font: "Arial" }),
                new TextRun({ text: " de ", size: 16, color: "999999", font: "Arial" }),
                new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: "999999", font: "Arial" })] })] }) },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/sessions/sweet-serene-babbage/mnt/outputs/FretMind_Auditoria_Arquitectura.docx", buf);
  console.log("OK", buf.length, "bytes");
});
