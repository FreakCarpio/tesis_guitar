

-- Habilitar extension necesaria
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ==========================================
-- TABLAS PRINCIPALES
-- ==========================================

CREATE TABLE IF NOT EXISTS niveles (
    id_nivel SERIAL PRIMARY KEY,
    nombre_nivel VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    orden INTEGER NOT NULL CHECK (orden > 0),
    criterio_subida TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL CHECK (LENGTH(TRIM(nombre)) >= 2),
    correo_electronico VARCHAR(150) UNIQUE NOT NULL CHECK (correo_electronico ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    password_hash VARCHAR(255) NOT NULL CHECK (LENGTH(password_hash) >= 60),
    id_nivel_actual INTEGER REFERENCES niveles(id_nivel),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_sesion TIMESTAMP,
    racha_dias INTEGER DEFAULT 0 CHECK (racha_dias >= 0),
    tiempo_total_practicado INTEGER DEFAULT 0 CHECK (tiempo_total_practicado >= 0),
    memoria_muscular_score DECIMAL(5,2) DEFAULT 0.00 CHECK (memoria_muscular_score BETWEEN 0 AND 100),
    preferencias_json JSONB DEFAULT '{}',
    estado_activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_ultima_sesion_posterior CHECK (ultima_sesion IS NULL OR ultima_sesion >= fecha_registro)
);

CREATE TABLE IF NOT EXISTS configuraciones_usuario (
    id_config SERIAL PRIMARY KEY,
    id_usuario INTEGER UNIQUE REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    notificaciones BOOLEAN DEFAULT TRUE,
    tiempo_objetivo_diario INTEGER DEFAULT 1800 CHECK (tiempo_objetivo_diario BETWEEN 60 AND 14400),
    nivel_dificultad_preferido VARCHAR(20) DEFAULT 'adaptive' CHECK (nivel_dificultad_preferido IN ('easy', 'normal', 'hard', 'adaptive')),
    tipo_guitarra VARCHAR(50) CHECK (tipo_guitarra IN ('acustica', 'electrica', 'clasica', 'ukelele', 'bajo')),
    afinacion_personalizada VARCHAR(20) DEFAULT 'EADGBE' CHECK (afinacion_personalizada ~ '^[A-G][#b]?[A-G][#b]?[A-G][#b]?[A-G][#b]?[A-G][#b]?[A-G][#b]?$'),
    modo_visual_ritmo VARCHAR(20) DEFAULT 'scroll' CHECK (modo_visual_ritmo IN ('scroll', 'bounce', 'static', 'progresion')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS acordes (
    id_acorde SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    nombre_normalizado VARCHAR(50) NOT NULL UNIQUE CHECK (nombre_normalizado ~ '^[a-z0-9_]+$'),
    tipo VARCHAR(30) CHECK (tipo IN ('mayor', 'menor', 'septima', 'mayor7', 'menor7', 'sus4', 'sus2', 'add9', 'dim', 'aug', 'power')),
    dificultad INTEGER CHECK (dificultad BETWEEN 1 AND 10),
    frecuencia_hz DECIMAL(8,2) CHECK (frecuencia_hz > 0 AND frecuencia_hz < 20000),
    diagrama_url TEXT,
    posicion_cuerdas JSONB NOT NULL CHECK (jsonb_array_length(posicion_cuerdas) >= 1),
    audio_referencia_url TEXT,
    notas_componentes VARCHAR(100) CHECK (notas_componentes ~ '^[A-G](#|b)?(-[A-G](#|b)?)*$'),
    popularidad INTEGER DEFAULT 0 CHECK (popularidad >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ejercicios (
    id_ejercicio SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL CHECK (LENGTH(TRIM(nombre)) >= 3),
    descripcion TEXT,
    tipo_ejercicio VARCHAR(50) NOT NULL CHECK (tipo_ejercicio IN ('acordes', 'escalas', 'ritmo', 'dedos', 'cambios', 'arpegios', 'lectura', 'improvisacion')),
    id_nivel INTEGER REFERENCES niveles(id_nivel),
    dificultad INTEGER CHECK (dificultad BETWEEN 1 AND 10),
    duracion_estimada_seg INTEGER CHECK (duracion_estimada_seg BETWEEN 30 AND 3600),
    objetivo TEXT,
    instrucciones TEXT,
    criterio_exito JSONB,
    data_ejercicio JSONB,
    activo BOOLEAN DEFAULT TRUE,
    veces_completado INTEGER DEFAULT 0 CHECK (veces_completado >= 0),
    puntuacion_media DECIMAL(5,2) CHECK (puntuacion_media BETWEEN 0 AND 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ejercicio_acordes (
    id SERIAL PRIMARY KEY,
    id_ejercicio INTEGER REFERENCES ejercicios(id_ejercicio) ON DELETE CASCADE,
    id_acorde INTEGER REFERENCES acordes(id_acorde) ON DELETE CASCADE,
    orden INTEGER CHECK (orden > 0),
    duracion_seg INTEGER CHECK (duracion_seg BETWEEN 1 AND 300),
    repeticiones INTEGER DEFAULT 1 CHECK (repeticiones BETWEEN 1 AND 100),
    UNIQUE(id_ejercicio, id_acorde, orden)
);

CREATE TABLE IF NOT EXISTS canciones (
    id_cancion SERIAL PRIMARY KEY,
    songsterr_id VARCHAR(50) UNIQUE,
    titulo VARCHAR(200) NOT NULL CHECK (LENGTH(TRIM(titulo)) >= 1),
    artista VARCHAR(150) CHECK (artista IS NULL OR LENGTH(TRIM(artista)) >= 1),
    album VARCHAR(150),
    dificultad INTEGER CHECK (dificultad BETWEEN 1 AND 10),
    tempo_bpm INTEGER CHECK (tempo_bpm BETWEEN 20 AND 300),
    tono VARCHAR(10) CHECK (tono ~ '^[A-G](#|b)?(m|maj|min|7|9|11|13)?$'),
    genero VARCHAR(50),
    fuente_api VARCHAR(50) DEFAULT 'Songsterr',
    url_tab TEXT,
    url_audio_preview TEXT,
    veces_practicada INTEGER DEFAULT 0 CHECK (veces_practicada >= 0),
    popularidad INTEGER DEFAULT 0 CHECK (popularidad BETWEEN 0 AND 100),
    acordes_json JSONB,
    acordes_unicos JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cancion_acordes (
    id SERIAL PRIMARY KEY,
    id_cancion INTEGER REFERENCES canciones(id_cancion) ON DELETE CASCADE,
    id_acorde INTEGER REFERENCES acordes(id_acorde),
    tiempo_inicio DECIMAL(6,2) CHECK (tiempo_inicio >= 0),
    duracion DECIMAL(6,2) CHECK (duracion > 0),
    compas INTEGER CHECK (compas > 0),
    parte VARCHAR(50) CHECK (parte IN ('intro', 'verso', 'precoro', 'coro', 'puente', 'solo', 'outro', 'interludio')),
    UNIQUE(id_cancion, tiempo_inicio)
);

CREATE TABLE IF NOT EXISTS sesiones_practica (
    id_sesion SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_ejercicio INTEGER REFERENCES ejercicios(id_ejercicio),
    id_cancion INTEGER REFERENCES canciones(id_cancion),
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMP,
    duracion_seg INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN fecha_fin IS NOT NULL THEN EXTRACT(EPOCH FROM (fecha_fin - fecha_inicio))::INTEGER
            ELSE NULL 
        END
    ) STORED,
    modo_practica VARCHAR(20) DEFAULT 'guiada' CHECK (modo_practica IN ('guiada', 'libre', 'evaluacion', 'desafio')),
    estado VARCHAR(20) DEFAULT 'en_progreso' CHECK (estado IN ('en_progreso', 'completada', 'abandonada', 'pausada')),
    notas_usuario TEXT,
    dispositivo_info JSONB,
    calificacion_usuario INTEGER CHECK (calificacion_usuario BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_tipo_sesion CHECK (
        (id_ejercicio IS NOT NULL AND id_cancion IS NULL) OR 
        (id_ejercicio IS NULL AND id_cancion IS NOT NULL) OR
        (id_ejercicio IS NULL AND id_cancion IS NULL)
    ),
    CONSTRAINT chk_fechas_sesion CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)
);

CREATE TABLE IF NOT EXISTS analisis_ia (
    id_analisis SERIAL PRIMARY KEY,
    id_sesion INTEGER UNIQUE REFERENCES sesiones_practica(id_sesion) ON DELETE CASCADE,
    timestamp_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    precision_general DECIMAL(5,2) CHECK (precision_general BETWEEN 0 AND 100),
    precision_notas DECIMAL(5,2) CHECK (precision_notas BETWEEN 0 AND 100),
    precision_ritmo DECIMAL(5,2) CHECK (precision_ritmo BETWEEN 0 AND 100),
    precision_tecnica DECIMAL(5,2) CHECK (precision_tecnica BETWEEN 0 AND 100),
    tempo_detectado INTEGER CHECK (tempo_detectado BETWEEN 20 AND 300),
    tempo_estabilidad DECIMAL(5,2) CHECK (tempo_estabilidad BETWEEN 0 AND 100),
    volumen_consistencia DECIMAL(5,2) CHECK (volumen_consistencia BETWEEN 0 AND 100),
    errores_detectados JSONB,
    acordes_mas_dificiles JSONB,
    patron_errores JSONB,
    feedback_ia_texto TEXT,
    sugerencias_mejora JSONB,
    recomendacion_siguiente INTEGER REFERENCES ejercicios(id_ejercicio),
    audio_url TEXT,
    espectrograma_data_url TEXT,
    raw_analysis_data JSONB,
    tiempo_procesamiento_ms INTEGER CHECK (tiempo_procesamiento_ms > 0),
    modelo_ia_version VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS detalle_notas (
    id_detalle SERIAL PRIMARY KEY,
    id_analisis INTEGER REFERENCES analisis_ia(id_analisis) ON DELETE CASCADE,
    tiempo_seg DECIMAL(6,2) NOT NULL CHECK (tiempo_seg >= 0),
    nota_esperada VARCHAR(10) CHECK (nota_esperada ~ '^[A-G](#|b)?[0-9]?$'),
    nota_detectada VARCHAR(10) CHECK (nota_detectada ~ '^[A-G](#|b)?[0-9]?$'),
    frecuencia_esperada_hz DECIMAL(8,2) CHECK (frecuencia_esperada_hz > 0),
    frecuencia_detectada_hz DECIMAL(8,2) CHECK (frecuencia_detectada_hz > 0),
    desviacion_cents DECIMAL(6,2),
    velocidad_ataque_ms INTEGER CHECK (velocidad_ataque_ms BETWEEN 0 AND 5000),
    sostenimiento_seg DECIMAL(4,2) CHECK (sostenimiento_seg >= 0),
    presion_estimada INTEGER CHECK (presion_estimada BETWEEN 1 AND 10),
    vibrato_detectado BOOLEAN,
    vibrato_frecuencia_hz DECIMAL(4,2),
    armonicos JSONB,
    calificacion DECIMAL(3,2) CHECK (calificacion BETWEEN 0 AND 1),
    confianza_ia DECIMAL(3,2) CHECK (confianza_ia BETWEEN 0 AND 1),
    id_acorde INTEGER REFERENCES acordes(id_acorde)
);

CREATE TABLE IF NOT EXISTS progresos (
    id_progreso SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    fecha DATE DEFAULT CURRENT_DATE,
    tiempo_practicado_seg INTEGER DEFAULT 0 CHECK (tiempo_practicado_seg >= 0),
    sesiones_completadas INTEGER DEFAULT 0 CHECK (sesiones_completadas >= 0),
    ejercicios_completados INTEGER DEFAULT 0 CHECK (ejercicios_completados >= 0),
    canciones_practicadas INTEGER DEFAULT 0 CHECK (canciones_practicadas >= 0),
    precision_promedio DECIMAL(5,2) CHECK (precision_promedio BETWEEN 0 AND 100),
    ritmo_promedio DECIMAL(5,2) CHECK (ritmo_promedio BETWEEN 0 AND 100),
    nivel_en_ese_momento INTEGER REFERENCES niveles(id_nivel),
    porcentaje_nivel_actual DECIMAL(5,2) CHECK (porcentaje_nivel_actual BETWEEN 0 AND 100),
    velocidad_cambio_acordes DECIMAL(5,2) CHECK (velocidad_cambio_acordes >= 0),
    consistencia_manos DECIMAL(5,2) CHECK (consistencia_manos BETWEEN 0 AND 100),
    acordes_dominados JSONB,
    areas_mejora JSONB,
    logros_desbloqueados JSONB,
    UNIQUE(id_usuario, fecha)
);

CREATE TABLE IF NOT EXISTS historial_ia (
    id_historial SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo_evento VARCHAR(50) CHECK (tipo_evento IN ('recomendacion_ejercicio', 'ajuste_dificultad', 'deteccion_problema', 'subida_nivel', 'feedback_generado', 'prediccion_error')),
    descripcion TEXT,
    contexto JSONB,
    decision_ia TEXT,
    resultado_evaluacion VARCHAR(20) CHECK (resultado_evaluacion IN ('exitoso', 'fallido', 'pendiente', 'parcial')),
    confianza_decision DECIMAL(3,2) CHECK (confianza_decision BETWEEN 0 AND 1)
);

-- INDICES B-TREE

CREATE INDEX IF NOT EXISTS idx_usuarios_nivel ON usuarios(id_nivel_actual);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(correo_electronico);
CREATE INDEX IF NOT EXISTS idx_usuarios_estado ON usuarios(estado_activo) WHERE estado_activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_ejercicios_nivel ON ejercicios(id_nivel);
CREATE INDEX IF NOT EXISTS idx_ejercicios_tipo ON ejercicios(tipo_ejercicio);
CREATE INDEX IF NOT EXISTS idx_ejercicios_activo ON ejercicios(activo) WHERE activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_sesiones_usuario_fecha ON sesiones_practica(id_usuario, fecha_inicio DESC);
CREATE INDEX IF NOT EXISTS idx_sesiones_estado ON sesiones_practica(estado);
CREATE INDEX IF NOT EXISTS idx_sesiones_modo ON sesiones_practica(modo_practica);
CREATE INDEX IF NOT EXISTS idx_analisis_precision ON analisis_ia(precision_general);
CREATE INDEX IF NOT EXISTS idx_analisis_recomendacion ON analisis_ia(recomendacion_siguiente);
CREATE INDEX IF NOT EXISTS idx_detalle_analisis ON detalle_notas(id_analisis);
CREATE INDEX IF NOT EXISTS idx_detalle_tiempo ON detalle_notas(id_analisis, tiempo_seg);
CREATE INDEX IF NOT EXISTS idx_detalle_acorde ON detalle_notas(id_acorde);
CREATE INDEX IF NOT EXISTS idx_progreso_usuario_fecha ON progresos(id_usuario, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_progreso_fecha ON progresos(fecha);
CREATE INDEX IF NOT EXISTS idx_canciones_dificultad ON canciones(dificultad);
CREATE INDEX IF NOT EXISTS idx_canciones_artista ON canciones(artista);
CREATE INDEX IF NOT EXISTS idx_acordes_dificultad ON acordes(dificultad);
CREATE INDEX IF NOT EXISTS idx_acordes_tipo ON acordes(tipo);
CREATE INDEX IF NOT EXISTS idx_historial_usuario ON historial_ia(id_usuario, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_historial_tipo ON historial_ia(tipo_evento);

-- INDICES GIN PARA JSONB

CREATE INDEX IF NOT EXISTS idx_gin_usuarios_preferencias ON usuarios USING GIN (preferencias_json);
CREATE INDEX IF NOT EXISTS idx_gin_ejercicios_data ON ejercicios USING GIN (data_ejercicio);
CREATE INDEX IF NOT EXISTS idx_gin_ejercicios_criterio ON ejercicios USING GIN (criterio_exito);
CREATE INDEX IF NOT EXISTS idx_gin_canciones_acordes ON canciones USING GIN (acordes_json);
CREATE INDEX IF NOT EXISTS idx_gin_sesiones_dispositivo ON sesiones_practica USING GIN (dispositivo_info);
CREATE INDEX IF NOT EXISTS idx_gin_analisis_errores ON analisis_ia USING GIN (errores_detectados);
CREATE INDEX IF NOT EXISTS idx_gin_analisis_sugerencias ON analisis_ia USING GIN (sugerencias_mejora);
CREATE INDEX IF NOT EXISTS idx_gin_analisis_raw ON analisis_ia USING GIN (raw_analysis_data);
CREATE INDEX IF NOT EXISTS idx_gin_progreso_acordes ON progresos USING GIN (acordes_dominados);
CREATE INDEX IF NOT EXISTS idx_gin_progreso_mejora ON progresos USING GIN (areas_mejora);
CREATE INDEX IF NOT EXISTS idx_gin_historial_contexto ON historial_ia USING GIN (contexto);
CREATE INDEX IF NOT EXISTS idx_gin_acordes_posicion ON acordes USING GIN (posicion_cuerdas jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_gin_detalle_armonicos ON detalle_notas USING GIN (armonicos jsonb_path_ops);


-- INDICES FULL-TEXT (TRIGRAM)

CREATE INDEX IF NOT EXISTS idx_trgm_canciones_titulo ON canciones USING gin (titulo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_trgm_canciones_artista ON canciones USING gin (artista gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_trgm_ejercicios_nombre ON ejercicios USING gin (nombre gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_trgm_analisis_feedback ON analisis_ia USING gin (feedback_ia_texto gin_trgm_ops);


-- VISTAS

CREATE OR REPLACE VIEW vista_resumen_diario AS
SELECT 
    u.id_usuario,
    u.nombre,
    u.correo_electronico,
    p.fecha,
    COALESCE(p.tiempo_practicado_seg, 0) / 60.0 as minutos_practicados,
    COALESCE(p.sesiones_completadas, 0) as sesiones_completadas,
    p.precision_promedio,
    n.nombre_nivel as nivel_actual,
    u.racha_dias,
    u.memoria_muscular_score,
    CASE 
        WHEN p.tiempo_practicado_seg >= c.tiempo_objetivo_diario THEN TRUE 
        ELSE FALSE 
    END as objetivo_diario_cumplido
FROM usuarios u
LEFT JOIN progresos p ON u.id_usuario = p.id_usuario AND p.fecha = CURRENT_DATE
LEFT JOIN niveles n ON u.id_nivel_actual = n.id_nivel
LEFT JOIN configuraciones_usuario c ON u.id_usuario = c.id_usuario;

CREATE OR REPLACE VIEW vista_ejercicios_por_nivel AS
SELECT 
    n.id_nivel,
    n.nombre_nivel,
    e.id_ejercicio,
    e.nombre as ejercicio,
    e.tipo_ejercicio,
    e.dificultad,
    e.duracion_estimada_seg,
    COUNT(ea.id_acorde) as num_acordes,
    ARRAY_AGG(a.nombre ORDER BY ea.orden) as acordes_lista
FROM niveles n
JOIN ejercicios e ON n.id_nivel = e.id_nivel
LEFT JOIN ejercicio_acordes ea ON e.id_ejercicio = ea.id_ejercicio
LEFT JOIN acordes a ON ea.id_acorde = a.id_acorde
WHERE e.activo = TRUE
GROUP BY n.id_nivel, n.nombre_nivel, n.orden, e.id_ejercicio, e.nombre, e.tipo_ejercicio, e.dificultad, e.duracion_estimada_seg
ORDER BY n.orden, e.dificultad;

CREATE OR REPLACE VIEW vista_estadisticas_semanal AS
SELECT 
    u.id_usuario,
    u.nombre,
    COUNT(DISTINCT s.id_sesion) as total_sesiones,
    COALESCE(SUM(s.duracion_seg), 0) / 60 as total_minutos,
    AVG(a.precision_general) as precision_promedio,
    MAX(s.fecha_inicio) as ultima_practica,
    COUNT(DISTINCT CASE WHEN s.estado = 'completada' THEN s.id_sesion END) as sesiones_completadas
FROM usuarios u
LEFT JOIN sesiones_practica s ON u.id_usuario = s.id_usuario 
    AND s.fecha_inicio >= CURRENT_DATE - INTERVAL '7 days'
LEFT JOIN analisis_ia a ON s.id_sesion = a.id_sesion
GROUP BY u.id_usuario, u.nombre;

CREATE OR REPLACE VIEW vista_acordes_dificiles AS
SELECT 
    u.id_usuario,
    u.nombre,
    a.nombre as acorde,
    COUNT(*) as total_intentos,
    AVG(d.calificacion) as calificacion_promedio,
    AVG(ABS(d.desviacion_cents)) as desviacion_promedio_cents
FROM usuarios u
JOIN sesiones_practica s ON u.id_usuario = s.id_usuario
JOIN analisis_ia ai ON s.id_sesion = ai.id_sesion
JOIN detalle_notas d ON ai.id_analisis = d.id_analisis
JOIN acordes a ON d.id_acorde = a.id_acorde
WHERE d.calificacion < 0.7 AND d.id_acorde IS NOT NULL
GROUP BY u.id_usuario, u.nombre, a.id_acorde, a.nombre
HAVING COUNT(*) >= 3
ORDER BY calificacion_promedio ASC;

-- FUNCIONES

CREATE OR REPLACE FUNCTION calcular_racha_dias(p_id_usuario INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_racha INTEGER := 0;
    v_fecha DATE;
BEGIN
    SELECT fecha INTO v_fecha
    FROM progresos
    WHERE id_usuario = p_id_usuario AND tiempo_practicado_seg > 0
    ORDER BY fecha DESC
    LIMIT 1;
    
    IF v_fecha IS NULL OR v_fecha < CURRENT_DATE - INTERVAL '1 day' THEN
        RETURN 0;
    END IF;
    
    v_racha := 1;
    WHILE EXISTS (
        SELECT 1 FROM progresos 
        WHERE id_usuario = p_id_usuario 
        AND fecha = v_fecha - (v_racha || ' days')::INTERVAL
        AND tiempo_practicado_seg > 0
    ) LOOP
        v_racha := v_racha + 1;
    END LOOP;
    
    RETURN v_racha;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION procesar_finalizacion_sesion()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = 'completada' AND OLD.estado != 'completada' THEN
        UPDATE usuarios 
        SET 
            tiempo_total_practicado = tiempo_total_practicado + COALESCE(NEW.duracion_seg, 0),
            ultima_sesion = NEW.fecha_fin,
            racha_dias = calcular_racha_dias(NEW.id_usuario)
        WHERE id_usuario = NEW.id_usuario;
        
        IF NEW.id_cancion IS NOT NULL THEN
            UPDATE canciones SET veces_practicada = veces_practicada + 1
            WHERE id_cancion = NEW.id_cancion;
        END IF;
        
        IF NEW.id_ejercicio IS NOT NULL THEN
            UPDATE ejercicios SET veces_completado = veces_completado + 1
            WHERE id_ejercicio = NEW.id_ejercicio;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION actualizar_progreso_diario()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = 'completada' AND OLD.estado != 'completada' THEN
        INSERT INTO progresos (id_usuario, fecha, tiempo_practicado_seg, sesiones_completadas)
        VALUES (NEW.id_usuario, CURRENT_DATE, COALESCE(NEW.duracion_seg, 0), 1)
        ON CONFLICT (id_usuario, fecha) 
        DO UPDATE SET
            tiempo_practicado_seg = progresos.tiempo_practicado_seg + EXCLUDED.tiempo_practicado_seg,
            sesiones_completadas = progresos.sesiones_completadas + 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- TRIGGERS


DROP TRIGGER IF EXISTS update_usuarios_updated_at ON usuarios;
CREATE TRIGGER update_usuarios_updated_at 
    BEFORE UPDATE ON usuarios 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_finalizar_sesion ON sesiones_practica;
CREATE TRIGGER trigger_finalizar_sesion
    AFTER UPDATE ON sesiones_practica
    FOR EACH ROW
    EXECUTE FUNCTION procesar_finalizacion_sesion();

DROP TRIGGER IF EXISTS trigger_actualizar_progreso ON sesiones_practica;
CREATE TRIGGER trigger_actualizar_progreso
    AFTER UPDATE ON sesiones_practica
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_progreso_diario();

-- SEGURIDAD: ROW LEVEL SECURITY (RLS)


ALTER TABLE sesiones_practica ENABLE ROW LEVEL SECURITY;
ALTER TABLE analisis_ia ENABLE ROW LEVEL SECURITY;
ALTER TABLE detalle_notas ENABLE ROW LEVEL SECURITY;
ALTER TABLE progresos ENABLE ROW LEVEL SECURITY;
ALTER TABLE historial_ia ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_sesiones_usuario ON sesiones_practica;
CREATE POLICY pol_sesiones_usuario ON sesiones_practica
    FOR ALL TO PUBLIC
    USING (id_usuario = current_setting('app.current_user_id')::INTEGER);

DROP POLICY IF EXISTS pol_analisis_usuario ON analisis_ia;
CREATE POLICY pol_analisis_usuario ON analisis_ia
    FOR ALL TO PUBLIC
    USING (id_sesion IN (SELECT id_sesion FROM sesiones_practica WHERE id_usuario = current_setting('app.current_user_id')::INTEGER));

DROP POLICY IF EXISTS pol_detalle_usuario ON detalle_notas;
CREATE POLICY pol_detalle_usuario ON detalle_notas
    FOR ALL TO PUBLIC
    USING (id_analisis IN (
        SELECT a.id_analisis FROM analisis_ia a
        JOIN sesiones_practica s ON a.id_sesion = s.id_sesion
        WHERE s.id_usuario = current_setting('app.current_user_id')::INTEGER
    ));

DROP POLICY IF EXISTS pol_progreso_usuario ON progresos;
CREATE POLICY pol_progreso_usuario ON progresos
    FOR ALL TO PUBLIC
    USING (id_usuario = current_setting('app.current_user_id')::INTEGER);

DROP POLICY IF EXISTS pol_historial_usuario ON historial_ia;
CREATE POLICY pol_historial_usuario ON historial_ia
    FOR ALL TO PUBLIC
    USING (id_usuario = current_setting('app.current_user_id')::INTEGER);


-- DATOS INICIALES (SEED)


INSERT INTO niveles (nombre_nivel, descripcion, orden, criterio_subida) VALUES
('Principiante', 'Primeros acordes y ritmos basicos', 1, 'Dominar C, G, D, Em, Am con 80% de precision'),
('Intermedio', 'Cambios de acordes fluidos y ritmos complejos', 2, 'Cambio de acordes > 60 por minuto, precision > 85%'),
('Avanzado', 'Tecnicas avanzadas y repertorio amplio', 3, 'Barres limpios, arpegios complejos, precision > 90%'),
('Experto', 'Dominio tecnico y expresion musical', 4, 'Improvisacion, composicion, precision consistente > 95%')
ON CONFLICT DO NOTHING;

INSERT INTO acordes (nombre, nombre_normalizado, tipo, dificultad, posicion_cuerdas, notas_componentes) VALUES
('C Mayor', 'c_major', 'mayor', 1, 
 '[{"cuerda": 5, "traste": 3, "dedo": 3}, {"cuerda": 4, "traste": 2, "dedo": 2}, {"cuerda": 2, "traste": 1, "dedo": 1}]', 
 'C-E-G'),
('G Mayor', 'g_major', 'mayor', 2, 
 '[{"cuerda": 6, "traste": 3, "dedo": 2}, {"cuerda": 5, "traste": 2, "dedo": 1}, {"cuerda": 1, "traste": 3, "dedo": 3}]', 
 'G-B-D'),
('D Mayor', 'd_major', 'mayor', 2, 
 '[{"cuerda": 3, "traste": 2, "dedo": 1}, {"cuerda": 2, "traste": 3, "dedo": 3}, {"cuerda": 1, "traste": 2, "dedo": 2}]', 
 'D-F#-A'),
('E Menor', 'e_minor', 'menor', 1, 
 '[{"cuerda": 5, "traste": 2, "dedo": 2}, {"cuerda": 4, "traste": 2, "dedo": 3}]', 
 'E-G-B'),
('A Menor', 'a_minor', 'menor', 1, 
 '[{"cuerda": 4, "traste": 2, "dedo": 2}, {"cuerda": 3, "traste": 2, "dedo": 3}, {"cuerda": 2, "traste": 1, "dedo": 1}]', 
 'A-C-E')
ON CONFLICT DO NOTHING;

-- VERIFICACION FINAL

SELECT 'BASE DE DATOS guitarai_app CREADA EXITOSAMENTE' as mensaje;
SELECT COUNT(*) as total_tablas FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
SELECT COUNT(*) as total_vistas FROM information_schema.views WHERE table_schema = 'public';
SELECT COUNT(*) as total_indices FROM pg_indexes WHERE schemaname = 'public';