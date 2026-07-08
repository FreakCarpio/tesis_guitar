const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, Header, Footer, TableOfContents, PageBreak
} = require("docx");

const GOLD="B8860B", DARK="15192A", RED="B00020", AMBER="C77800",
      GREEN="2E7D32", GREY="555555", BLUE="1F4E79", PURPLE="5B3A9B";
const CW=9360;

const P=(text,o={})=>new Paragraph({spacing:{after:o.after??120,before:o.before??0,line:276},alignment:o.align,
  children:[new TextRun({text,bold:o.bold,italics:o.italics,color:o.color,size:o.size,font:"Arial"})]});
const runs=(arr,o={})=>new Paragraph({spacing:{after:o.after??120,before:o.before??0,line:276},alignment:o.align,
  children:arr.map(r=>new TextRun({text:r.t,bold:r.b,italics:r.i,color:r.c,font:r.mono?"Consolas":"Arial",size:r.size??22}))});
const H1=t=>new Paragraph({heading:HeadingLevel.HEADING_1,children:[new TextRun({text:t,font:"Arial"})]});
const H2=t=>new Paragraph({heading:HeadingLevel.HEADING_2,children:[new TextRun({text:t,font:"Arial"})]});
const H3=t=>new Paragraph({heading:HeadingLevel.HEADING_3,children:[new TextRun({text:t,font:"Arial"})]});
const bullet=(t,lvl=0)=>new Paragraph({numbering:{reference:"bullets",level:lvl},spacing:{after:80,line:268},
  children:Array.isArray(t)?t.map(r=>new TextRun({text:r.t,bold:r.b,italics:r.i,color:r.c,font:r.mono?"Consolas":"Arial",size:22})):[new TextRun({text:t,font:"Arial",size:22})]});
const num=t=>new Paragraph({numbering:{reference:"nums",level:0},spacing:{after:90,line:268},
  children:Array.isArray(t)?t.map(r=>new TextRun({text:r.t,bold:r.b,italics:r.i,color:r.c,font:"Arial",size:22})):[new TextRun({text:t,font:"Arial",size:22})]});
const spacer=()=>new Paragraph({children:[],spacing:{after:60}});

function codeBlock(lines){
  return new Paragraph({shading:{fill:"F4F4F4",type:ShadingType.CLEAR},spacing:{after:140,before:40,line:240},
    border:{left:{style:BorderStyle.SINGLE,size:18,color:GOLD,space:6}},
    children:lines.flatMap((l,i)=>{const r=[new TextRun({text:l,font:"Consolas",size:18,color:"333333"})];if(i<lines.length-1)r.push(new TextRun({break:1}));return r;})});
}
function cell(text,{w,fill,bold,color,align,size}={}){
  const b={style:BorderStyle.SINGLE,size:1,color:"CCCCCC"};
  const content=Array.isArray(text)
    ? text.map(line=>new Paragraph({alignment:align,spacing:{after:30,line:250},
        children:[new TextRun({text:line.t??line,bold:line.b??bold,italics:line.i,color:line.c??color,font:line.mono?"Consolas":"Arial",size:line.size??size??18})]}))
    : [new Paragraph({alignment:align,spacing:{after:0,line:250},children:[new TextRun({text,bold,color,font:"Arial",size:size??18})]})];
  return new TableCell({width:{size:w,type:WidthType.DXA},shading:fill?{fill,type:ShadingType.CLEAR}:undefined,
    margins:{top:60,bottom:60,left:110,right:110},borders:{top:b,bottom:b,left:b,right:b},children:content});
}
function table(widths,headers,rows,headFill=DARK){
  const head=new TableRow({tableHeader:true,children:headers.map((h,i)=>cell(h,{w:widths[i],fill:headFill,bold:true,color:"FFFFFF",size:18}))});
  const body=rows.map((r,ri)=>new TableRow({children:r.map((c,i)=>{
    const o=c&&typeof c==="object"&&!Array.isArray(c);
    const txt=o?c.t:c;
    return cell(txt,{w:widths[i],fill:o&&c.fill?c.fill:(ri%2?"FAFAFA":undefined),bold:o?c.b:false,color:o?c.c:undefined,align:o?c.align:undefined});
  })}));
  return new Table({width:{size:CW,type:WidthType.DXA},columnWidths:widths,rows:[head,...body]});
}
const pri=p=>{const m={P0:RED,P1:AMBER,P2:BLUE,P3:GREEN};return{t:p,b:true,c:"FFFFFF",fill:m[p],align:AlignmentType.CENTER};};

const children=[];

// PORTADA
children.push(
  new Paragraph({spacing:{before:2000,after:0},alignment:AlignmentType.CENTER,children:[new TextRun({text:"FretMind",bold:true,size:66,color:DARK,font:"Arial"})]}),
  new Paragraph({spacing:{after:40},alignment:AlignmentType.CENTER,children:[new TextRun({text:"Diseño de la siguiente etapa de producto",italics:true,size:26,color:GREY,font:"Arial"})]}),
  new Paragraph({spacing:{before:460,after:0},alignment:AlignmentType.CENTER,border:{top:{style:BorderStyle.SINGLE,size:6,color:GOLD,space:8},bottom:{style:BorderStyle.SINGLE,size:6,color:GOLD,space:8}},
    children:[new TextRun({text:"DE HERRAMIENTA A EXPERIENCIA DE APRENDIZAJE",bold:true,size:30,color:GOLD,font:"Arial"})]}),
  new Paragraph({spacing:{before:560},alignment:AlignmentType.CENTER,children:[new TextRun({text:"Roadmap de producto · UX · Priorización P0–P3",size:24,color:DARK,font:"Arial"})]}),
  new Paragraph({spacing:{before:120},alignment:AlignmentType.CENTER,children:[new TextRun({text:"Benchmark: Duolingo · GuitarTuna · Yousician",size:22,color:GREY,font:"Arial"})]}),
  new Paragraph({spacing:{before:1300},alignment:AlignmentType.CENTER,children:[new TextRun({text:"Documento de Product Owner y Arquitectura",size:22,color:GREY,font:"Arial"})]}),
  new Paragraph({spacing:{before:120},alignment:AlignmentType.CENTER,children:[new TextRun({text:"Autor del proyecto: Alejandro Guzmán",size:22,color:GREY,font:"Arial"})]}),
  new Paragraph({spacing:{before:120},alignment:AlignmentType.CENTER,children:[new TextRun({text:"Alcance: diseño de producto — sin implementación de código",size:20,italics:true,color:GREY,font:"Arial"})]}),
  new Paragraph({children:[new PageBreak()]})
);

// TOC
children.push(H1("Tabla de contenidos"));
children.push(new TableOfContents("Tabla de contenidos",{hyperlink:true,headingStyleRange:"1-2"}));
children.push(new Paragraph({children:[new PageBreak()]}));

// 0. TL;DR
children.push(H1("0. Síntesis para el Product Owner"));
children.push(P("FretMind ya resolvió su base técnica: backend en Railway, MongoDB Atlas, login Google, afinador con DSP, búsqueda Songsterr, Wilfredo IA y MVVM. Eso es infraestructura, no experiencia. Hoy el producto es una caja de herramientas (afinador + buscador + chat + analizador) sin un hilo conductor que enganche al usuario."));
children.push(runs([{t:"La tesis de esta etapa: ",b:true},{t:"convertir la caja de herramientas en un ",},{t:"viaje de aprendizaje con hábito diario",b:true},{t:". Duolingo, GuitarTuna y Yousician no ganan por tener más funciones, sino por tres cosas que FretMind aún no tiene: un ",},{t:"camino guiado",b:true},{t:", un ",},{t:"bucle diario motivador",b:true},{t:" (racha, meta, XP, celebración) y una ",},{t:"dificultad que se adapta en tiempo real",b:true},{t:" con feedback real del micrófono.",}]));
children.push(runs([{t:"North-star metric propuesta: ",b:true},{t:"minutos de práctica activa por semana y retención de racha (D1/D7/D30). Todo lo P0/P1 existe para mover esa métrica.",}]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 1. ESTADO ACTUAL
children.push(H1("1. Estado actual del producto"));
children.push(P("Lectura honesta antes de diseñar: FretMind tiene músculo técnico pero le falta el esqueleto de producto. Las piezas existen aisladas; falta el tejido que las une en una experiencia."));
children.push(H2("1.1 Qué ya funciona (activos)"));
children.push(bullet("Backend desplegado (Railway) + MongoDB Atlas con colecciones ya creadas (usuarios, sesiones, progreso, estadísticas, historial, configuraciones, calibración, ejercicios desbloqueados)."));
children.push(bullet("Login con Google real de extremo a extremo y endpoints de perfil."));
children.push(bullet("Afinador con pipeline DSP de calidad y captura de audio real (AudioRecord)."));
children.push(bullet("Búsqueda de canciones (Songsterr) con pantalla de detalle."));
children.push(bullet("Wilfredo (tutor por reglas) y arquitectura MVVM conectada en varias pantallas."));
children.push(H2("1.2 Qué falta para competir (brechas de producto)"));
children.push(bullet([{t:"No hay onboarding ni activación: ",b:true},{t:"el usuario entra y no sabe qué hacer primero. No existe el momento de primer logro (first win).",}]));
children.push(bullet([{t:"No hay camino de aprendizaje: ",b:true},{t:"no existe un mapa de progresión (skill tree / misiones) que diga qué sigue.",}]));
children.push(bullet([{t:"No hay bucle de hábito: ",b:true},{t:"racha, meta diaria, XP y recordatorios no existen como mecánica real; las métricas de Home/Progress son cálculos inventados.",}]));
children.push(bullet([{t:"No hay práctica con feedback en vivo: ",b:true},{t:"la pantalla de práctica es un flujo simulado; el motor de audio no alimenta una experiencia tipo Yousician.",}]));
children.push(bullet([{t:"Herramientas sin pulir: ",b:true},{t:"el afinador (ventaja competitiva directa vs GuitarTuna) aún se muestra con datos mock en la UI.",}]));
children.push(H2("1.3 Benchmark competitivo"));
children.push(table([1900,3730,3730],
  ["Referente","Qué hace excepcional","Qué debe adoptar FretMind"],
  [
    ["GuitarTuna",{t:"Afinador instantáneo y delicioso; valor en <10s; fricción casi cero.",},"Convertir el afinador en el primer win: preciso, visual, instantáneo."],
    ["Yousician",{t:"Feedback nota a nota en tiempo real sobre canciones/ejercicios; misiones y scoring.",},"Modo práctica play-along con detección en vivo (ya hay DSP + Songsterr)."],
    ["Duolingo",{t:"Motor de hábito: racha, meta diaria, XP, ligas, lecciones cortas, repaso espaciado, mascota.",},"Camino guiado + bucle diario + Wilfredo como mascota emocional."],
  ]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 2. VISION Y PRINCIPIOS
children.push(H1("2. Visión de producto y principios de diseño"));
children.push(runs([{t:"Visión: ",b:true},{t:"“La forma más simple y motivadora de aprender guitarra: cada día, 10 minutos, con un maestro (Wilfredo) que te escucha de verdad y ajusta el camino a tu ritmo.”",i:true}]));
children.push(H2("2.1 Principios rectores"));
children.push(num([{t:"Valor en menos de 60 segundos. ",b:true},{t:"El usuario debe lograr algo (afinar, tocar un acorde) casi al instante.",}]));
children.push(num([{t:"Siempre una sola acción siguiente. ",b:true},{t:"La app nunca deja al usuario preguntándose qué hacer.",}]));
children.push(num([{t:"Cada sesión termina con progreso visible. ",b:true},{t:"Estrellas, XP, racha, barra que sube.",}]));
children.push(num([{t:"El feedback es real, no cosmético. ",b:true},{t:"Los números salen del DSP, no de fórmulas inventadas.",}]));
children.push(num([{t:"Wilfredo es el hilo emocional. ",b:true},{t:"Mascota-coach que celebra, explica y acompaña (rol de “Duo”).",}]));
children.push(num([{t:"Dificultad en zona de flow. ",b:true},{t:"Ni aburrido ni frustrante: apuntar a ~80% de éxito por sesión.",}]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 3. MARCO PRIORIDADES
children.push(H1("3. Marco de priorización P0–P3"));
children.push(P("Toda decisión de esta etapa se etiqueta con una prioridad. La regla: una prioridad más baja no se empieza hasta que la superior esté sana. El criterio es el impacto sobre la experiencia y la métrica norte, no la dificultad técnica."));
children.push(table([1100,3100,5160],
  ["Nivel","Significado","Por qué existe"],
  [
    [pri("P0"),{t:"Cimiento y correctitud. Sin esto, nada de lo demás es creíble.",b:true},"Bugs que rompen la confianza, datos reales y la activación mínima. Un producto con métricas falsas o afinador mock no puede competir ni demostrarse."],
    [pri("P1"),{t:"Diferenciación central.",b:true},"Es lo que hace a FretMind competir: camino guiado, práctica en vivo, IA adaptativa y bucle diario. Aquí vive el valor único."],
    [pri("P2"),{t:"Retención y profundidad.",b:true},"Mantiene al usuario semanas y meses: logros, repaso espaciado, perfil real, coaching proactivo."],
    [pri("P3"),{t:"Futuro / expansión.",b:true},"Alto valor pero prematuro: social, monetización, multi-instrumento, offline. Distraen si se hacen antes de tiempo."],
  ]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 4. ROADMAP POR FASES
children.push(H1("4. Roadmap de producto por fases"));
children.push(P("Cinco fases de producto (no técnicas). Cada fase entrega una experiencia completa y comprobable con usuarios, no una lista de tareas internas."));
children.push(table([1500,2600,3560,1700],
  ["Fase","Nombre","Resultado para el usuario","Prioridad"],
  [
    [{t:"Fase 1",b:true},"Cimiento confiable","La app muestra datos reales y las herramientas (afinador) funcionan de verdad.",pri("P0")],
    [{t:"Fase 2",b:true},"Activación y primer logro","Desde instalar hasta tocar algo y ver progreso en <3 minutos.",pri("P0")],
    [{t:"Fase 3",b:true},"El viaje guiado","Camino de aprendizaje + práctica con feedback en vivo + celebración.",pri("P1")],
    [{t:"Fase 4",b:true},"Hábito que engancha","Racha, meta diaria, XP, adaptación real y recordatorios.",pri("P1")],
    [{t:"Fase 5",b:true},"Profundidad y permanencia","Logros, repaso espaciado, perfil, repertorio y coaching de Wilfredo.",pri("P2")],
  ]));
children.push(P("Todo lo que quede fuera de estas fases (social, monetización, offline, multi-instrumento) es P3 y se aborda en una versión futura (sección 15)."));
children.push(new Paragraph({children:[new PageBreak()]}));

// 5. ACTIVACION
children.push(H1("5. De instalar a la primera práctica (activación)"));
children.push(P("Este es el flujo más importante del producto: decide si el usuario se queda o desinstala. Objetivo: primer logro real en menos de 3 minutos, con la mínima fricción posible."));
children.push(H2("5.1 Recorrido paso a paso"));
children.push(num([{t:"Splash de marca (<2s). ",b:true},{t:"Logo FretMind + Wilfredo asomando. Nada de esperas largas.",}]));
children.push(num([{t:"Bienvenida en 3 tarjetas. ",b:true},{t:"“Aprende”, “Afina”, “Progresa”. Deslizable y saltable.",}]));
children.push(num([{t:"Login con Google (un toque). ",b:true},{t:"Ya implementado. Sin formularios ni contraseñas.",}]));
children.push(num([{t:"Diagnóstico con Wilfredo (30–45s). ",b:true},{t:"3–4 preguntas: ¿ya tocas?, objetivo (canciones/técnica/teoría), ¿tienes guitarra a mano?, tiempo diario (define la meta). Esto inicializa el perfil adaptativo.",}]));
children.push(num([{t:"Permiso de micrófono con contexto. ",b:true},{t:"“Wilfredo necesita escucharte para ayudarte.” Se pide justo antes de usarlo, no al azar.",}]));
children.push(num([{t:"Primer win: afinar. ",b:true},{t:"“Afinemos tu guitarra.” Éxito casi garantizado → primera dosis de logro.",}]));
children.push(num([{t:"Primera micro-práctica guiada. ",b:true},{t:"Un ejercicio simple (p. ej. acorde Em o cambio C→G) con feedback en vivo. Al terminar: estrellas + XP + “Racha: día 1”.",}]));
children.push(num([{t:"Home con la siguiente acción clara. ",b:true},{t:"Anillo de meta diaria, racha encendida y botón “Continuar”.",}]));
children.push(H2("5.2 Regla de oro de la activación"));
children.push(runs([{t:"Si el usuario no logra afinar o tocar algo en su primera sesión, la activación falló. ",b:true},{t:"Cada pantalla previa al primer win debe justificar su existencia o eliminarse. La fricción es el enemigo número uno.",}]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 6. FLUJO UX
children.push(H1("6. Flujo UX completo"));
children.push(H2("6.1 El bucle central (core loop)"));
children.push(codeBlock([
  "                 +--------------------------+",
  "                 |   HOME (hub del día)     |",
  "                 |  meta diaria · racha ·   |",
  "                 |  “Continuar” (siguiente) |",
  "                 +------------+-------------+",
  "                              |",
  "                              v",
  "         +--------------------------------------+",
  "         |  SESIÓN DE PRÁCTICA (guiada)         |",
  "         |  ejercicio -> tocar -> feedback DSP  |",
  "         +--------------------+-----------------+",
  "                              |",
  "                              v",
  "         +--------------------------------------+",
  "         |  RESULTADO / CELEBRACIÓN             |",
  "         |  estrellas · XP · racha · Wilfredo   |",
  "         +--------------------+-----------------+",
  "                              |",
  "                              v  (progreso guardado en Mongo)",
  "                    vuelve a HOME actualizado",
]));
children.push(P("El bucle debe cerrarse en 3–10 minutos. Alrededor del bucle viven las utilidades: Afinador, Canciones (Songsterr), Wilfredo (chat) y Perfil."));
children.push(H2("6.2 Arquitectura de navegación propuesta"));
children.push(bullet([{t:"Barra inferior (5 destinos máximo): ",b:true},{t:"Aprender (camino), Afinador, Canciones, Wilfredo, Perfil.",}]));
children.push(bullet([{t:"Home = pestaña “Aprender”. ",b:true},{t:"Es el hub: meta del día, racha, y el camino de lecciones.",}]));
children.push(bullet([{t:"Práctica y Resultado son pantallas de flujo (full-screen), ",},{t:"no pestañas: se entra, se completa y se vuelve.",}]));
children.push(H2("6.3 Estados que no pueden faltar"));
children.push(bullet("Vacío (primer día, sin historial): mostrar el camino y empujar al primer ejercicio."));
children.push(bullet("Sin micrófono / permiso denegado: modo degradado + cómo activarlo."));
children.push(bullet("Sin conexión: afinador y ejercicios offline básicos deben seguir dando valor (P3 para offline completo)."));
children.push(bullet("Racha en riesgo: aviso claro antes de perderla."));
children.push(new Paragraph({children:[new PageBreak()]}));

// 7. PANTALLAS NUEVAS
children.push(H1("7. Pantallas nuevas que deberían existir"));
children.push(table([2600,4760,2000],
  ["Pantalla","Propósito","Prioridad"],
  [
    ["Onboarding / Bienvenida","3 tarjetas de valor antes del login.",pri("P0")],
    ["Diagnóstico (Wilfredo)","Cuestionario de nivel, objetivo y meta diaria; inicializa la IA.",pri("P0")],
    ["Priming de micrófono","Pide permiso con contexto emocional, justo antes de usarlo.",pri("P0")],
    ["Camino de aprendizaje","Mapa tipo skill-tree/misiones: el corazón del viaje.",pri("P1")],
    ["Reproductor de lección","Ejercicio guiado paso a paso con instrucciones y demo.",pri("P1")],
    ["Práctica en vivo (play-along)","Detección nota a nota sincronizada a la tablatura (Yousician).",pri("P1")],
    ["Resultado / Celebración","Estrellas, XP, racha y mensaje de Wilfredo al cerrar la sesión.",pri("P1")],
    ["Meta diaria / Racha","Anillo de progreso del día y calendario de racha.",pri("P1")],
    ["Logros / Insignias","Hitos de racha, precisión, canciones dominadas.",pri("P2")],
    ["Ajustes / Recordatorios","Hora de recordatorio, sonido, afinación preferida.",pri("P2")],
    ["Paywall / Premium","Suscripción (solo cuando exista retención).",pri("P3")],
  ]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 8. PANTALLAS ELIMINAR/REDISEÑAR
children.push(H1("8. Pantallas actuales: eliminar o rediseñar"));
children.push(H2("8.1 Eliminar"));
children.push(bullet([{t:"Wilfredoscreen.kt — ",b:true},{t:"duplicado huérfano del chat. Se conserva una sola pantalla de Wilfredo (ChatScreen).",}]));
children.push(H2("8.2 Rediseñar"));
children.push(table([2300,4260,2800],
  ["Pantalla","Rediseño","Prioridad"],
  [
    ["Home","De tarjetas estáticas a hub del día: anillo de meta, racha real, “Continuar” y el camino.",pri("P0")],
    ["Afinador (Tuner)","Conectar a TunerEngine real (hoy mock). Nivel GuitarTuna: aguja/visual claro, feedback instantáneo.",pri("P0")],
    ["Progreso","De números inventados a métricas reales en el tiempo: radar de habilidades, historial, calendario de racha.",pri("P1")],
    ["Perfil","Darle ruta en navegación y conectarlo al backend: nivel, stats reales, ajustes.",pri("P1")],
    ["Práctica","De flujo simulado a reproductor de lección/práctica en vivo con feedback DSP.",pri("P1")],
    ["Búsqueda + Detalle de canción","Añadir botón “Practicar esta canción” que lance el modo play-along.",pri("P1")],
    ["Splash","Mantener, pero delgado (<2s) y con marca.",pri("P2")],
  ]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 9. MONGODB
children.push(H1("9. Qué debe almacenarse en MongoDB"));
children.push(P("Las colecciones ya existen; falta llenarlas con datos de producto reales. El foco: identidad, progreso, gamificación y estado adaptativo. Nada de métricas cosméticas."));
children.push(table([2500,4260,2600],
  ["Colección","Qué guardar (nivel producto)","Prioridad"],
  [
    ["usuarios","Identidad Google (sub, email, nombre, foto), nivel, objetivo, meta diaria (min), instrumento, fecha de alta.",pri("P0")],
    ["estadisticas / perfil","Estado adaptativo: precisión, consistencia, error y maestría por habilidad; dificultad actual.",pri("P0")],
    ["sesiones","Cada práctica: ejercicio, duración, puntuación, métricas DSP, timestamp.",pri("P0")],
    ["progreso","Avance en el camino: unidades/lecciones completas, estrellas, ejercicios desbloqueados.",pri("P1")],
    ["gamificacion (nueva o en usuarios)","Racha actual, última fecha activa, XP total, logros obtenidos.",pri("P1")],
    ["historial","Log de eventos para analítica y para el motor de repaso espaciado.",pri("P2")],
    ["configuraciones","Recordatorios (hora), sonido, afinación preferida, idioma.",pri("P2")],
    ["calibracion","Perfil de ruido por usuario/dispositivo para el afinador.",pri("P2")],
    ["canciones_guardadas (nueva)","Favoritos de Songsterr y su nivel de dominio por usuario.",pri("P2")],
  ]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 10. IA ADAPTATIVA
children.push(H1("10. Cómo debe trabajar la IA adaptativa"));
children.push(P("Hoy existe un promedio exponencial de tres métricas. Para competir, debe evolucionar de “promedio global” a “director del viaje”: qué practicar, a qué dificultad y cuándo repasar."));
children.push(H2("10.1 Entradas"));
children.push(bullet("Métricas DSP por sesión: precisión de nota, consistencia/tiempo, tasa de error, afinación."));
children.push(bullet("Finalización y dificultad percibida (¿fue fácil/difícil?)."));
children.push(bullet("Historial: qué habilidades se practicaron y hace cuánto."));
children.push(H2("10.2 Cómo decide"));
children.push(num([{t:"Maestría por habilidad. ",b:true},{t:"Mantener un valor 0–1 por habilidad (acordes, ritmo, digitación, afinación) con el promedio exponencial ya existente, extendido por skill.",}]));
children.push(num([{t:"Controlador de dificultad (zona de flow). ",b:true},{t:"Subir o bajar la dificultad del siguiente ejercicio para mantener ~80% de éxito.",}]));
children.push(num([{t:"Repaso espaciado. ",b:true},{t:"Reprogramar habilidades débiles para revisión (estilo SM-2 / práctica de Duolingo).",}]));
children.push(num([{t:"Siguiente mejor ejercicio. ",b:true},{t:"Recomendar en Home qué toca hoy, combinando maestría baja + repaso pendiente + objetivo del usuario.",}]));
children.push(H2("10.3 Cómo se comunica"));
children.push(bullet([{t:"Wilfredo es la voz de la IA: ",b:true},{t:"“Hoy repasamos el cambio C→G porque ayer se te resistió.” La adaptación se siente como un coach, no como un algoritmo.",}]));
children.push(bullet([{t:"Arranque en frío: ",b:true},{t:"el diagnóstico inicial fija la dificultad de partida; las primeras sesiones calibran rápido.",}]));
children.push(bullet([{t:"Guardarraíles: ",b:true},{t:"nunca castigar; bajar dificultad con gracia y celebrar la mejora, no solo el resultado absoluto.",}]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 11. EVOLUCION USUARIO
children.push(H1("11. Cómo evoluciona el usuario durante meses"));
children.push(P("El producto debe diseñar el arco de retención, no solo la primera sesión. Cada tramo tiene un objetivo emocional y un gancho para volver."));
children.push(table([1700,3000,2560,2100],
  ["Momento","Qué vive el usuario","Gancho de retención","Prioridad"],
  [
    ["Día 0","Se activa, afina y toca algo. Racha = 1.","Primer logro + promesa de mañana.",pri("P0")],
    ["Semana 1","5–10 min diarios: afinar + 1 lección. Wilfredo lo anima.","Meta diaria + racha + recordatorio.",pri("P1")],
    ["Semanas 2–4","Toca sus primeras canciones simples; el camino se ramifica.","Insignias + primeras canciones dominadas.",pri("P1")],
    ["Meses 2–3","Camino intermedio, técnica, canciones más difíciles.","Hitos de racha (30/60) + repaso adaptativo.",pri("P2")],
    ["Meses 4–6","Repertorio propio, dominio, objetivos a largo plazo.","Contenido nuevo + reto adaptativo constante.",pri("P2")],
    ["Recuperación","Si pierde la racha o se va.","Congelar racha + camino de regreso + push.",pri("P2")],
  ]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 12. MODULOS PRIORIDAD
children.push(H1("12. Módulos por prioridad"));
children.push(H2("P0 — Cimiento confiable"));
children.push(bullet("Datos reales de sesión y progreso (matar métricas inventadas)."));
children.push(bullet("Afinador conectado al motor real."));
children.push(bullet("Onboarding + diagnóstico + primer win (activación)."));
children.push(bullet("Reproductor de práctica guiada con feedback real."));
children.push(H2("P1 — Diferenciación central"));
children.push(bullet("Camino de aprendizaje (skill tree / misiones)."));
children.push(bullet("Práctica en vivo play-along sobre canciones."));
children.push(bullet("Motor adaptativo v1 (maestría por habilidad + dificultad + siguiente ejercicio)."));
children.push(bullet("Bucle de hábito: racha, meta diaria, XP, celebración, recordatorios."));
children.push(H2("P2 — Retención y profundidad"));
children.push(bullet("Logros/insignias, calendario e hitos de racha."));
children.push(bullet("Repaso espaciado."));
children.push(bullet("Perfil y estadísticas reales; ajustes."));
children.push(bullet("Coaching proactivo de Wilfredo; canciones guardadas."));
children.push(H2("P3 — Futuro"));
children.push(bullet("Social/ligas, monetización, multi-instrumento, offline completo, modo profesor."));
children.push(new Paragraph({children:[new PageBreak()]}));

// 13. BUGS
children.push(H1("13. Bugs a corregir antes de seguir (P0)"));
children.push(P("Estos rompen la credibilidad del producto y deben cerrarse antes de construir el viaje encima."));
children.push(bullet([{t:"Afinador en modo mock: ",b:true},{t:"la pantalla no usa el TunerEngine real pese a existir captura de audio. Es la ventaja directa vs GuitarTuna y hoy es de mentira.",}]));
children.push(bullet([{t:"Métricas inventadas en Home/Progreso: ",b:true},{t:"cálculos como streak = precisión×10 no representan nada; deben venir de datos reales.",}]));
children.push(bullet([{t:"Progreso y Perfil sin datos reales: ",b:true},{t:"Progreso muestra valores ficticios y Perfil no está cableado ni con ruta en navegación.",}]));
children.push(bullet([{t:"Lectura de progreso con hack de audio: ",b:true},{t:"si aún se envía un WAV falso para “leer” progreso, separar lectura de escritura con endpoints propios.",}]));
children.push(bullet([{t:"CORS abierto: ",b:true},{t:"allow_origins=[\"*\"] con allow_credentials=True es inválido e inseguro; restringir a orígenes conocidos.",}]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 14. DEUDA TECNICA
children.push(H1("14. Deuda técnica a eliminar"));
children.push(P("No bloquea el diseño, pero frena la velocidad y la escala. Priorizada como P1–P2 según impacto."));
children.push(table([4500,2860,2000],
  ["Deuda","Impacto","Prioridad"],
  [
    ["Driver Mongo síncrono (MongoClient) en FastAPI async","Bloquea el event loop bajo carga; migrar a Motor/Beanie o wrappear.",pri("P1")],
    ["Contrato de respuesta inconsistente (wrapper solo en algunos endpoints)","Parsing dispar y frágil; estandarizar un único envoltorio.",pri("P1")],
    ["Pantalla duplicada Wilfredoscreen","Código muerto y confusión; eliminar.",pri("P1")],
    ["applicationId com.example.prueba (placeholder)","No publicable; definir identidad real.",pri("P2")],
    ["Errores devueltos como HTTP 200","Manejo de errores y analítica pobres.",pri("P2")],
    ["Sin tests ni CI","Regresiones al crecer; añadir mínimos.",pri("P2")],
    ["Nomenclatura/estructura (carpetas con ñ y espacios, mezcla idiomas)","Fricción de tooling y mantenimiento.",pri("P2")],
  ]));
children.push(new Paragraph({children:[new PageBreak()]}));

// 15. FUTURO
children.push(H1("15. Funcionalidades para una versión futura (P3)"));
children.push(P("Alto potencial, pero prematuras: hacerlas antes de tener retención sólida dispersa el esfuerzo."));
children.push(bullet("Social: ligas, tablas de clasificación, amigos y retos (motor de retención Duolingo, pero requiere masa de usuarios)."));
children.push(bullet("Monetización: suscripción Premium, prueba gratuita, paywall — solo cuando el bucle diario retenga."));
children.push(bullet("Multi-instrumento (bajo, ukelele), zurdos y biblioteca de afinaciones alternativas."));
children.push(bullet("Modo offline completo y detección de pitch on-device para latencia mínima en play-along."));
children.push(bullet("Contenido generado/curado: cursos temáticos, artistas, teoría avanzada; modo profesor/aula."));
children.push(new Paragraph({children:[new PageBreak()]}));

// 16. TABLA CONSOLIDADA
children.push(H1("16. Prioridades consolidadas y por qué existen"));
children.push(table([1000,4400,3960],
  ["Prio.","Qué incluye","Por qué esta prioridad"],
  [
    [pri("P0"),"Datos reales, afinador real, onboarding + primer win, práctica guiada con feedback, CORS.","Sin credibilidad ni activación no hay producto que retener ni demostrar. Es la línea de base innegociable."],
    [pri("P1"),"Camino de aprendizaje, play-along en vivo, adaptativo v1, bucle de hábito (racha/meta/XP), rediseño de Home/Progreso/Perfil/Práctica.","Es la diferenciación: lo que hace a FretMind competir con Yousician y Duolingo y mover la métrica norte."],
    [pri("P2"),"Logros, repaso espaciado, perfil/stats, coaching proactivo, ajustes, canciones guardadas, gran parte de la deuda técnica.","Convierte usuarios activos en usuarios de meses; sube retención D30 y profundidad de uso."],
    [pri("P3"),"Social, monetización, multi-instrumento, offline, modo profesor.","Escala y negocio: valioso pero prematuro; se hace cuando el núcleo ya retiene."],
  ]));
children.push(spacer());
children.push(H2("16.1 Métricas de éxito por prioridad"));
children.push(bullet([{t:"P0: ",b:true},{t:"% de usuarios que completan la primera práctica (activación) y tiempo hasta el primer win.",}]));
children.push(bullet([{t:"P1: ",b:true},{t:"retención D1/D7, minutos de práctica por semana, longitud media de racha.",}]));
children.push(bullet([{t:"P2: ",b:true},{t:"retención D30, sesiones por usuario/mes, habilidades dominadas.",}]));
children.push(bullet([{t:"P3: ",b:true},{t:"conversión a Premium, viralidad (invitaciones), ingresos por usuario.",}]));
children.push(spacer());
children.push(runs([{t:"Cierre. ",b:true},{t:"FretMind ya ganó la batalla técnica. La siguiente etapa es de producto: darle un viaje, un hábito y un maestro que escucha. Ejecutando P0→P1 en orden, FretMind deja de ser una caja de herramientas y empieza a competir de verdad en experiencia con Duolingo, GuitarTuna y Yousician.",}]));

// DOC
const doc=new Document({
  creator:"Product Owner / Arquitectura",
  title:"FretMind — Diseño de la siguiente etapa de producto",
  styles:{default:{document:{run:{font:"Arial",size:22}}},
    paragraphStyles:[
      {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:30,bold:true,font:"Arial",color:DARK},
        paragraph:{spacing:{before:240,after:160},outlineLevel:0,border:{bottom:{style:BorderStyle.SINGLE,size:6,color:GOLD,space:4}}}},
      {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:25,bold:true,font:"Arial",color:BLUE},
        paragraph:{spacing:{before:200,after:120},outlineLevel:1}},
      {id:"Heading3",name:"Heading 3",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:22,bold:true,font:"Arial",color:"333333"},
        paragraph:{spacing:{before:140,after:80},outlineLevel:2}},
    ]},
  numbering:{config:[
    {reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:600,hanging:280}}}}]},
    {reference:"nums",levels:[{level:0,format:LevelFormat.DECIMAL,text:"%1.",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:600,hanging:280}}}}]},
  ]},
  sections:[{
    properties:{page:{size:{width:12240,height:15840},margin:{top:1440,right:1440,bottom:1440,left:1440}}},
    headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,border:{bottom:{style:BorderStyle.SINGLE,size:4,color:"DDDDDD",space:4}},
      children:[new TextRun({text:"FretMind · Diseño de la siguiente etapa de producto",size:16,color:"999999",font:"Arial"})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,
      children:[new TextRun({text:"Página ",size:16,color:"999999",font:"Arial"}),new TextRun({children:[PageNumber.CURRENT],size:16,color:"999999",font:"Arial"}),
                new TextRun({text:" de ",size:16,color:"999999",font:"Arial"}),new TextRun({children:[PageNumber.TOTAL_PAGES],size:16,color:"999999",font:"Arial"})]})]})},
    children
  }]
});
Packer.toBuffer(doc).then(buf=>{fs.writeFileSync("/sessions/sweet-serene-babbage/mnt/outputs/FretMind_Roadmap_Producto.docx",buf);console.log("OK",buf.length,"bytes");});
