"""
Base de Conocimiento de guitarra (MC6).

Contenido pedagógico CURADO y versionado en código (misma filosofía que el
catálogo de ejercicios y el camino): teoría, técnica, acordes, escalas,
postura, afinación y ejercicios. RIFF la consulta para responder con
contenido real en modo reglas y, cuando se active un LLM, como grounding
(RAG ligero) para reducir alucinaciones.

Recuperación determinística: `buscar(consulta, nivel, k)` puntúa por
coincidencia de keywords y título normalizados. Sin embeddings por ahora:
si algún día se quiere recuperación semántica, se cambia la implementación
de `buscar` sin tocar a los consumidores.
"""

import unicodedata


def _norm(texto: str) -> str:
    """minúsculas + sin acentos + solo alfanumérico/espacios."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return "".join(c if c.isalnum() or c.isspace() else " " for c in t)


def _e(id, categoria, titulo, contenido, keywords, nivel="principiante", relacionados=None):
    return {
        "id": id, "categoria": categoria, "titulo": titulo,
        "contenido": contenido, "keywords": keywords, "nivel": nivel,
        "relacionados": relacionados or [],
    }


ENTRADAS = [
    # ------------------------------ TEORÍA ------------------------------
    _e("notas-musicales", "teoria", "Las notas musicales y el cifrado americano",
       "Las 7 notas son Do, Re, Mi, Fa, Sol, La, Si. En cifrado americano: C, D, E, F, G, A, B. "
       "En guitarra casi todo se escribe en cifrado: Am es La menor, G es Sol Mayor. "
       "Entre nota y nota hay un tono, salvo Mi→Fa y Si→Do, que están a medio tono (un traste).",
       ["notas", "cifrado", "americano", "do re mi", "nombres"]),
    _e("tono-semitono", "teoria", "Tono y semitono en el diapasón",
       "Un semitono = 1 traste; un tono = 2 trastes. Es la regla de oro para moverte por el "
       "mástil: si subes 2 trastes en la misma cuerda, subiste un tono.",
       ["tono", "semitono", "traste", "distancia", "intervalo basico"]),
    _e("intervalos", "teoria", "Intervalos: la distancia entre notas",
       "Un intervalo es la distancia entre dos notas (3ª, 5ª, 8ª...). La 3ª define si un acorde "
       "es mayor (alegre) o menor (melancólico); la 5ª le da estabilidad. Los power chords son "
       "solo fundamental y 5ª, por eso no suenan ni mayores ni menores.",
       ["intervalo", "tercera", "quinta", "octava", "distancia"], "intermedio"),
    _e("acorde-mayor-menor", "teoria", "¿Por qué un acorde es mayor o menor?",
       "Un acorde tiene 3 notas: fundamental, 3ª y 5ª. Si la 3ª es mayor (2 tonos desde la "
       "fundamental) el acorde suena alegre: C, G, D. Si es menor (1.5 tonos), suena triste: "
       "Am, Em, Dm. La diferencia entre C y Cm es UNA sola nota.",
       ["mayor", "menor", "acorde", "triada", "alegre", "triste", "diferencia"]),
    _e("acorde-septima", "teoria", "Acordes de séptima",
       "Al acorde básico se le suma una 4ª nota (la 7ª). B7, E7, A7 son típicos en blues y para "
       "dar tensión antes de resolver: E7 pide volver a A. Empieza con E7 y A7, son formas fáciles.",
       ["septima", "7", "b7", "e7", "a7", "blues", "tension"], "intermedio"),
    _e("compas-4-4", "teoria", "El compás de 4/4",
       "El 4/4 divide la música en grupos de 4 pulsos: cuentas 1-2-3-4 y vuelves a empezar. "
       "Casi todo el rock y pop está en 4/4. El vals usa 3/4 (1-2-3). Acentúa el 1 para no perderte.",
       ["compas", "4/4", "pulso", "ritmo", "contar", "vals", "3/4"]),
    _e("tempo-bpm", "teoria", "Tempo y BPM",
       "El tempo se mide en BPM (pulsos por minuto): 60 BPM = 1 pulso por segundo. Practica "
       "lento (50-70 BPM) hasta tocar limpio y sube de 5 en 5. La velocidad es consecuencia de "
       "la precisión, nunca al revés.",
       ["tempo", "bpm", "velocidad", "metronomo", "lento", "rapido"]),
    _e("tonalidad", "teoria", "¿Qué es la tonalidad?",
       "La tonalidad es la 'casa' de una canción: en tonalidad de Sol, el acorde G suena a "
       "reposo y los demás giran a su alrededor. Las tonalidades amigables en guitarra son G, C, "
       "D, Em y Am, porque usan acordes abiertos.",
       ["tonalidad", "clave", "key", "casa", "reposo"], "intermedio"),
    _e("progresion-i-iv-v", "teoria", "La progresión I-IV-V",
       "Miles de canciones usan los grados I, IV y V de la tonalidad: en Sol son G, C y D; en La "
       "son A, D y E. Si además sumas el vi (Em en Sol), tienes la progresión pop por excelencia: "
       "G-Em-C-D.",
       ["progresion", "i iv v", "grados", "1 4 5", "pop", "canciones"], "intermedio"),
    _e("capo-transporte", "teoria", "El capo y el transporte",
       "El capo sube toda la guitarra de tono: con capo en 2, una forma de Am suena como Bm. "
       "Sirve para cantar más cómodo o usar acordes abiertos en tonalidades difíciles. Cada "
       "traste de capo = medio tono arriba.",
       ["capo", "cejilla mecanica", "transporte", "transportar", "tono arriba"]),

    # ------------------------------ ACORDES ------------------------------
    _e("acorde-am", "acordes", "Acorde Am (La menor)",
       "Am: índice en 1ª cuerda... no: índice en cuerda 2 traste 1, medio en cuerda 4 traste 2, "
       "anular en cuerda 3 traste 2. No toques la 6ª cuerda. Es el primer acorde menor que todo "
       "guitarrista aprende y aparece en miles de canciones.",
       ["am", "la menor", "primer acorde", "digitacion am"]),
    _e("acorde-c", "acordes", "Acorde C (Do Mayor)",
       "C: índice en cuerda 2 traste 1, medio en cuerda 4 traste 2, anular en cuerda 5 traste 3. "
       "Evita la 6ª cuerda. El reto es que la 1ª cuerda suene al aire sin que el índice la roce: "
       "curva bien los dedos.",
       ["c", "do mayor", "do", "digitacion c"]),
    _e("acorde-g", "acordes", "Acorde G (Sol Mayor)",
       "G: medio en cuerda 6 traste 3, índice en cuerda 5 traste 2, anular (o meñique) en cuerda "
       "1 traste 3. Suenan las 6 cuerdas. Practica el cambio C→G: es de los más usados y de los "
       "que más cuesta al inicio.",
       ["g", "sol mayor", "sol", "digitacion g"]),
    _e("acorde-d", "acordes", "Acorde D (Re Mayor)",
       "D: índice en cuerda 3 traste 2, medio en cuerda 1 traste 2, anular en cuerda 2 traste 3. "
       "Solo suenan las 4 cuerdas agudas. Forma un triángulo con los dedos; si la 1ª cuerda "
       "zumba, revisa el arco del medio.",
       ["d", "re mayor", "re", "digitacion d", "triangulo"]),
    _e("acorde-e-em", "acordes", "Acordes E y Em (Mi Mayor y menor)",
       "Em: medio y anular en cuerdas 5 y 4, traste 2 — el acorde más fácil, suenan las 6 "
       "cuerdas. E: añade el índice en cuerda 3 traste 1. Escucha la diferencia mayor/menor "
       "quitando y poniendo ese dedo: es la 3ª del acorde.",
       ["e", "em", "mi mayor", "mi menor", "facil", "primer acorde"]),
    _e("acorde-dm", "acordes", "Acorde Dm (Re menor)",
       "Dm: índice en cuerda 1 traste 1, medio en cuerda 3 traste 2, anular en cuerda 2 traste 3. "
       "Solo 4 cuerdas agudas. Suena melancólico; aparece mucho junto a Am y C.",
       ["dm", "re menor", "digitacion dm"], "intermedio"),
    _e("acorde-f-cejilla", "acordes", "Acorde F: la primera cejilla",
       "F: el índice pisa TODAS las cuerdas en el traste 1 (cejilla) y el resto forma un E. "
       "Trucos: coloca el índice ligeramente de canto, cerca del traste; aprieta con el peso del "
       "brazo, no solo con el pulgar; y empieza con la versión pequeña (solo cuerdas 1-4). Es "
       "normal que tome semanas.",
       ["f", "fa", "cejilla", "barra", "barre", "dificil", "no suena"], "intermedio",
       ["tecnica-cejilla"]),
    _e("power-chords", "acordes", "Power chords (quintas)",
       "El power chord usa fundamental y 5ª (p. ej. índice en 6ª cuerda y anular dos trastes "
       "más arriba en la 5ª). Es la base del rock: una sola forma movible por todo el mástil. "
       "Silencia las cuerdas agudas con la palma o el índice.",
       ["power", "quinta", "rock", "movible", "distorsion"], "intermedio"),
    _e("cambios-limpios", "acordes", "Cambios de acordes sin pausas",
       "Para cambiar limpio: 1) mueve todos los dedos A LA VEZ, no uno por uno; 2) prepara la "
       "forma en el aire antes de aterrizar; 3) busca dedos ancla que no se mueven (Am→C solo "
       "mueve un dedo); 4) practica el cambio aislado 1 minuto en bucle contando cuántos logras.",
       ["cambio", "cambios", "lento", "pausa", "fluido", "ancla", "transicion"]),
    _e("trasteo", "acordes", "¿Por qué zumban las cuerdas? (trasteo)",
       "El zumbido/trasteo sale de: dedos lejos del traste (acércalos justo detrás del metal), "
       "poca presión, dedos planos que rozan cuerdas vecinas (curva las falanges) o uñas largas "
       "en la mano izquierda. Toca cuerda por cuerda del acorde para encontrar la culpable.",
       ["zumba", "zumbido", "trastea", "buzz", "no suena", "sucio", "muerta"]),

    # ------------------------------ ESCALAS ------------------------------
    _e("escala-mayor", "escalas", "La escala mayor",
       "La escala mayor sigue el patrón T-T-S-T-T-T-S (tono/semitono). Do mayor: C D E F G A B C. "
       "Es la referencia de toda la teoría. Practícala lenta, un dedo por traste, subiendo y "
       "bajando sin cortar el sonido.",
       ["escala mayor", "do mayor", "patron", "ttsttts"]),
    _e("pentatonica-menor", "escalas", "La pentatónica menor",
       "5 notas y el 90% de los solos de rock y blues. La posición 1 de Am pentatónica vive entre "
       "los trastes 5 y 8. Apréndela como caja: cada cuerda usa 2 notas. Con esta sola posición "
       "ya puedes improvisar sobre Am o C.",
       ["pentatonica", "menor", "solo", "improvisar", "blues", "rock", "caja"], "intermedio"),
    _e("pentatonica-mayor", "escalas", "La pentatónica mayor",
       "La misma forma que la menor pero desplazada: la pentatónica de C mayor usa las mismas "
       "notas que la de Am (relativa menor). Suena country/pop, más 'alegre' que la menor.",
       ["pentatonica mayor", "relativa", "country"], "avanzado"),
    _e("escala-cromatica", "escalas", "La escala cromática como ejercicio",
       "La cromática toca TODOS los semitonos (todos los trastes seguidos). Musicalmente se usa "
       "poco, pero es el mejor calentamiento: dedos 1-2-3-4 en trastes consecutivos, cuerda por "
       "cuerda, con metrónomo.",
       ["cromatica", "calentamiento", "1234", "todos los trastes"]),
    _e("como-practicar-escalas", "escalas", "Cómo practicar escalas sin aburrirse",
       "1) Siempre con metrónomo, empieza a 60 BPM. 2) Sube 5 BPM solo tras 3 pasadas limpias. "
       "3) Alterna subida/bajada y patrones (de 3 en 3 notas). 4) Canta o di el nombre de las "
       "notas mientras las tocas: conecta oído, mano y teoría.",
       ["practicar escalas", "aburrido", "metronomo", "patrones"]),

    # ------------------------------ TÉCNICA ------------------------------
    _e("pua-alternada", "tecnica", "Púa alternada",
       "Alterna siempre abajo-arriba (↓↑↓↑), incluso al cambiar de cuerda. Sujeta la púa entre "
       "pulgar e índice sin tensión, que asome poco (3-4 mm). El movimiento sale de la muñeca, "
       "no del codo. Empieza en una sola cuerda con metrónomo.",
       ["pua", "alternada", "picking", "abajo arriba", "muneca"]),
    _e("tecnica-fingerstyle", "tecnica", "Fingerstyle: la mano p-i-m-a",
       "p = pulgar (cuerdas 6-5-4), i = índice (3ª), m = medio (2ª), a = anular (1ª). Cada dedo "
       "tiene su cuerda: así el cerebro automatiza. La mano flota sin apoyar la palma; el pulgar "
       "siempre por delante de los demás dedos.",
       ["fingerstyle", "fingerpicking", "pima", "dedos", "pulgar", "arpegios mano"]),
    _e("tecnica-cejilla", "tecnica", "Técnica de cejilla sin dolor",
       "La cejilla no es fuerza bruta: 1) índice ligeramente de canto (borde óseo); 2) codo "
       "pegado al cuerpo; 3) el pulgar detrás como apoyo, la presión real viene de tirar el "
       "brazo hacia ti; 4) el mástil algo elevado ayuda. Si duele la mano en 30 segundos, estás "
       "apretando de más.",
       ["cejilla", "barre", "duele", "fuerza", "f", "bm"], "intermedio", ["acorde-f-cejilla"]),
    _e("ligados", "tecnica", "Hammer-on y pull-off (ligados)",
       "Hammer-on: martilla un dedo sobre el traste sin volver a tocar la cuerda. Pull-off: al "
       "levantar, 'rasca' ligeramente la cuerda hacia abajo para que siga sonando. Dan fluidez a "
       "los solos y ahorran púa. Practícalos en bucle 5→7 en cada cuerda.",
       ["hammer", "pull", "ligado", "legato", "martillo"], "intermedio"),
    _e("palm-mute", "tecnica", "Palm mute",
       "Apoya el canto de la palma derecha sobre las cuerdas JUSTO en el puente (no más adelante) "
       "y toca: sonido percusivo y contenido, la base del rock rítmico. Cuanto más avanzas la "
       "palma, más apagado; encuentra el punto donde aún se distingue la nota.",
       ["palm", "mute", "apagar", "chunk", "percusivo", "puente"], "intermedio"),
    _e("rasgueo-ddu-udu", "tecnica", "El rasgueo universal D-DU-UDU",
       "El patrón ↓ ↓↑ ↑↓↑ sirve para cientos de canciones. Clave: el brazo NUNCA deja de moverse "
       "abajo-arriba como un péndulo constante; los silencios son pasadas sin tocar las cuerdas. "
       "Cuenta '1, 2 y, y 4 y' mientras rasgueas.",
       ["rasgueo", "ddu udu", "strumming", "patron", "pendulo", "wonderwall"]),
    _e("slides", "tecnica", "Slides (deslizamientos)",
       "Toca una nota y desliza el dedo por la cuerda sin soltar la presión hasta el traste "
       "destino. Mantén presión constante durante el viaje. Conecta frases y da un sonido vocal "
       "a los solos.",
       ["slide", "deslizar", "glissando"], "intermedio"),
    _e("bending-vibrato", "tecnica", "Bending y vibrato",
       "Bending: empuja la cuerda hacia arriba para subir el tono (apóyate con varios dedos y "
       "gira la muñeca, no empujes solo con el dedo). Vibrato: oscilaciones pequeñas y regulares "
       "de ese mismo movimiento. Afina el bending con un objetivo: debe llegar a la nota del "
       "traste siguiente (medio tono) o dos (un tono).",
       ["bending", "bend", "vibrato", "estirar", "expresion"], "avanzado"),

    # ------------------------------ POSTURA ------------------------------
    _e("postura-sentado", "postura", "Postura sentado",
       "Espalda recta sin rigidez, guitarra apoyada en la pierna derecha (o izquierda estilo "
       "clásico, más ergonómico para estudiar), mástil ligeramente hacia arriba. La guitarra se "
       "sostiene sola entre pecho y brazo: si la sujetas con la mano izquierda, esa tensión te "
       "roba técnica.",
       ["postura", "sentado", "espalda", "pierna", "ergonomia"]),
    _e("mano-izquierda", "postura", "La mano izquierda y el pulgar",
       "Pulgar detrás del mástil, más o menos a la altura del dedo medio, como pinza suave. "
       "Muñeca recta, dedos curvados cayendo perpendiculares sobre las cuerdas, yemas justo "
       "detrás del traste. Si el pulgar asoma por arriba al hacer acordes abiertos está bien; "
       "para cejillas y escalas, atrás.",
       ["mano izquierda", "pulgar", "muneca", "dedos curvados", "posicion"]),
    _e("mano-derecha", "postura", "La mano derecha",
       "Con púa: muñeca suelta flotando sobre el puente, movimiento de muñeca y no de codo. Sin "
       "púa: antebrazo apoyado en el aro, mano flotando en ángulo natural. En ambos casos: cero "
       "tensión en el hombro — revísalo cada pocos minutos.",
       ["mano derecha", "pua agarre", "flotar", "hombro", "tension"]),
    _e("dolor-dedos", "postura", "Dolor de dedos y callos",
       "Las yemas duelen las primeras 2-3 semanas: es normal y pasa cuando salen los callos. "
       "Sesiones cortas y frecuentes (15 min diarios) forman callos mejor que maratones. Si el "
       "dolor es en la muñeca, el pulgar o el antebrazo, eso NO es normal: revisa postura y "
       "presión, y descansa.",
       ["dolor", "dedos", "callos", "duele", "yemas", "cuanto dura"]),
    _e("tension-descansos", "postura", "Tensión y descansos",
       "La tensión es el enemigo silencioso: hombros subidos, mandíbula apretada, pulgar "
       "estrangulando el mástil. Cada 10-15 minutos: suelta los brazos, respira, sacude las "
       "manos. Tocar relajado no es un lujo, es la técnica más importante de todas.",
       ["tension", "relajado", "descanso", "pausa", "hombros"]),

    # ------------------------------ AFINACIÓN ------------------------------
    _e("afinacion-estandar", "afinacion", "Afinación estándar EADGBE",
       "De la cuerda más grave a la más aguda: Mi(E2), La(A2), Re(D3), Sol(G3), Si(B3), Mi(E4). "
       "Truco nemotécnico: 'El Amor De Gente Buena Existe'. Afina siempre ANTES de practicar: "
       "entrenar el oído con una guitarra desafinada enseña notas equivocadas.",
       ["afinacion", "estandar", "eadgbe", "cuerdas", "nombres cuerdas"]),
    _e("como-afinar", "afinacion", "Cómo afinar con el afinador",
       "Toca UNA cuerda al aire, deja que suene y mira el indicador: si marca bajo, tensa "
       "girando la clavija poco a poco; si marca alto, afloja. Mejor llegar a la nota subiendo "
       "(afloja de más y tensa hasta afinar): así la cuerda mantiene mejor la afinación.",
       ["afinar", "afinador", "clavija", "alto", "bajo", "cents"]),
    _e("drop-d", "afinacion", "Afinación Drop D",
       "Baja solo la 6ª cuerda de E a D (un tono). Permite power chords con un solo dedo y un "
       "grave más profundo. Muchas canciones de rock la usan; FretMind te muestra la afinación "
       "que cada canción necesita en su detalle.",
       ["drop d", "drop", "dadgbe", "afinacion alternativa"], "intermedio"),
    _e("porque-desafina", "afinacion", "¿Por qué se desafina la guitarra?",
       "Causas: cuerdas nuevas que aún se estiran (estíralas suavemente con la mano), cambios de "
       "temperatura y humedad, clavijas flojas, o tocar muy fuerte. Las cuerdas nuevas tardan "
       "1-2 días en asentarse: reafina varias veces al principio.",
       ["desafina", "no mantiene", "cuerdas nuevas", "temperatura", "estirar"]),

    # ------------------------------ EJERCICIOS ------------------------------
    _e("ejercicio-arana", "ejercicios", "La araña (1-2-3-4)",
       "Dedos 1-2-3-4 en trastes consecutivos, cuerda por cuerda, subiendo y bajando. Es EL "
       "ejercicio de independencia y calentamiento. Regla: los dedos que no tocan se quedan "
       "CERCA de la cuerda, no vuelan lejos. Lento y con metrónomo vale el doble.",
       ["arana", "1234", "independencia", "calentamiento", "dedos"]),
    _e("ejercicio-cambio-1min", "ejercicios", "Cambios de acordes en 1 minuto",
       "Elige DOS acordes (p. ej. Am→C). Pon 1 minuto de reloj y cuenta cuántos cambios limpios "
       "logras. Anota el número e inténtalo superar mañana. Es la forma más medible de mejorar "
       "cambios: compites contra ti, no contra el metrónomo.",
       ["un minuto", "cambios", "contar", "medir", "am c"]),
    _e("como-usar-metronomo", "ejercicios", "Cómo usar el metrónomo",
       "Empieza SIEMPRE a un tempo donde toques perfecto (aunque parezca ridículamente lento). "
       "Sube 5 BPM solo tras 3 pasadas limpias seguidas; si fallas dos veces, baja 10. El "
       "metrónomo no es un juez: es un espejo de tu precisión.",
       ["metronomo", "como usar", "subir tempo", "bpm", "click"]),
    _e("rutina-15-min", "ejercicios", "Rutina de 15 minutos",
       "2 min calentamiento (araña) + 5 min técnica del día (el ejercicio que te recomienda "
       "RIFF) + 5 min cambios de acordes o canción + 3 min libre para disfrutar. Quince minutos "
       "DIARIOS vencen a dos horas del domingo: el cerebro consolida durmiendo.",
       ["rutina", "15 minutos", "diaria", "poco tiempo", "organizar"]),
    _e("memoria-muscular", "ejercicios", "Cómo se construye la memoria muscular",
       "La memoria muscular se graba con repeticiones LENTAS y correctas: cada repetición rápida "
       "y sucia también se graba... mal. Regla 3x: si sale limpio 3 veces seguidas, puedes "
       "acelerar un poco. Dormir bien consolida lo practicado ese día.",
       ["memoria muscular", "repeticiones", "lento", "automatico", "habito"]),

    # --------------------- FAQ / CONCEPTOS BÁSICOS ---------------------
    _e("que-es-acorde", "teoria", "¿Qué es un acorde?",
       "Un acorde es un grupo de 3 o más notas que suenan a la vez y se llevan bien entre sí. "
       "En la guitarra lo formas pisando varias cuerdas con la mano izquierda y rasgueándolas "
       "juntas. Son el esqueleto de casi cualquier canción: con 4 o 5 acordes básicos (C, G, D, "
       "Em, Am) ya puedes acompañar cientos de temas. Empieza por Em y Am, que son los más "
       "cómodos para la mano.",
       ["que es un acorde", "que es acorde", "acorde", "definicion acorde",
        "que son los acordes"]),
    _e("que-es-escala", "escalas", "¿Qué es una escala?",
       "Una escala es una serie ordenada de notas que suben o bajan siguiendo un patrón de "
       "distancias, como los peldaños de una escalera. Sirven para crear melodías y solos, "
       "entrenar el oído y ganar agilidad en los dedos. Las dos que más vas a usar al inicio: "
       "la escala mayor (el famoso Do-Re-Mi) y la pentatónica menor, la favorita del rock y el "
       "blues. Practícalas lento y con metrónomo: son tu gimnasio musical.",
       ["que es una escala", "que es escala", "escala", "definicion escala",
        "para que sirven las escalas", "que son las escalas"]),
    _e("que-es-afinar", "afinacion", "¿Qué significa afinar?",
       "Afinar es ajustar la tensión de cada cuerda (girando su clavija) hasta que vibre "
       "exactamente a la frecuencia que le corresponde: más tensa suena más aguda, más floja "
       "más grave. Una guitarra desafinada hace que TODO suene mal aunque toques perfecto, y "
       "además acostumbra mal a tu oído. Por eso se afina siempre antes de practicar: el "
       "Afinador de FretMind te guía cuerda por cuerda en menos de un minuto.",
       ["que significa afinar", "que es afinar", "para que afinar", "afinado",
        "desafinado", "por que afinar"]),
    _e("tablatura", "teoria", "¿Qué es una tablatura?",
       "La tablatura (o tab) es la forma más fácil de leer música para guitarra: 6 líneas que "
       "representan las 6 cuerdas (la de arriba es la 1ª, la más aguda) y números que indican "
       "en qué traste pisar. Un 0 es cuerda al aire; un 3 en la línea de abajo es 6ª cuerda, "
       "traste 3. No necesitas saber solfeo: se lee de izquierda a derecha y los números "
       "apilados en vertical se tocan a la vez (acorde).",
       ["tablatura", "tab", "tabs", "leer tablatura", "que es una tablatura",
        "numeros", "partitura"]),
    _e("arpegios", "tecnica", "¿Qué son los arpegios?",
       "Un arpegio es tocar las notas de un acorde una por una en vez de todas a la vez: pisas "
       "el acorde normal y haces sonar las cuerdas por separado, dejándolas resonar. Da ese "
       "sonido de balada o intro delicada (piensa en «Nothing Else Matters»). Es el siguiente "
       "paso natural cuando ya te salen los acordes: mismo esfuerzo de mano izquierda, nueva "
       "musicalidad. Empieza arpegiando Em: 6ª cuerda con el pulgar y luego 3-2-1.",
       ["arpegio", "arpegios", "que son los arpegios", "que es un arpegio",
        "nota por nota", "balada"]),
    _e("cuerdas-numeracion", "afinacion", "Cómo se numeran las cuerdas",
       "Las cuerdas se cuentan desde la MÁS AGUDA (la más delgada, abajo cuando tocas): esa es "
       "la 1ª (Mi agudo, E4). La 6ª es la más gruesa y grave (Mi grave, E2), la que queda "
       "arriba, más cerca de tu cara. El orden completo de la 6ª a la 1ª es: Mi-La-Re-Sol-Si-Mi "
       "(E-A-D-G-B-E). Ojo: confundir la numeración es normal al inicio porque la 1ª está "
       "'abajo', pero en cifras y tablaturas siempre se usa esta convención.",
       ["sexta cuerda", "primera cuerda", "segunda cuerda", "tercera cuerda",
        "cuarta cuerda", "quinta cuerda", "que cuerda", "cual es la sexta",
        "cual es la primera", "numeracion", "orden de las cuerdas", "mas grave",
        "mas aguda", "gruesa", "delgada"]),
]

_POR_ID = {e["id"]: e for e in ENTRADAS}

CATEGORIAS = sorted({e["categoria"] for e in ENTRADAS})


def obtener(entrada_id: str) -> dict | None:
    return _POR_ID.get(entrada_id)


def buscar(consulta: str, nivel: str | None = None, k: int = 3) -> list[dict]:
    """Top-k entradas por coincidencia de keywords/título (determinístico)."""
    q = _norm(consulta)
    tokens = set(q.split())
    palabras = [p for p in q.split() if len(p) > 2]
    if not q.strip():
        return []

    puntuadas = []
    for e in ENTRADAS:
        score = 0.0
        for kw in e["keywords"]:
            kwn = _norm(kw).strip()
            if not kwn:
                continue
            if " " in kwn:
                # Frase: substring sobre la consulta completa.
                if kwn in q:
                    score += 3.0
            elif len(kwn) <= 3:
                # Keywords cortas ("e", "am", "f"): solo como palabra exacta,
                # nunca como substring (matchearían en cualquier texto).
                if kwn in tokens:
                    score += 2.0
            elif kwn in q:
                score += 2.0
        titulo = _norm(e["titulo"])
        for p in palabras:
            if p in titulo:
                score += 1.0
        if nivel and e["nivel"] == nivel:
            score += 0.5
        if score > 0:
            puntuadas.append((score, e))

    puntuadas.sort(key=lambda x: (-x[0], x[1]["id"]))
    return [e for _, e in puntuadas[:max(1, min(10, k))]]
