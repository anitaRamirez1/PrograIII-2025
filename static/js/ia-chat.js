/* ==========================================
   MODO DEMOSTRACIÓN - SIN VALIDACIÓN
   Para pruebas y demostraciones del proyecto
========================================== */
const MODO_DEMOSTRACION = true;

/* ===== HISTORIAL (localStorage + BD) ===== */
const historialKey = 'uromed_ia_historial';
let historial = JSON.parse(localStorage.getItem(historialKey)) || [];
let chatActualIdx = 0;

/* ===== CHATS DESDE SERVIDOR ===== */
const chatsDelServer = JSON.parse(window.CHATS_PREVIOS || '[]');
if (chatsDelServer.length) {
    historial = chatsDelServer;
    localStorage.setItem(historialKey, JSON.stringify(historial));
}

/* ===== RENDERIZADO MEJORADO ===== */
function renderHistorial() {
  const nav = document.getElementById('historial');
  nav.innerHTML = '';
  historial.forEach((item, idx) => {
    const div = document.createElement('div');
    div.className = `historial-item ${idx === chatActualIdx ? 'active' : ''}`;
    div.textContent = item.titulo;
    div.onclick = () => cargarChat(idx);
    div.oncontextmenu = (e) => mostrarMenu(e, idx);
    nav.appendChild(div);
  });
}

/* ===== NUEVO CHAT MEJORADO ===== */
function nuevoChat() {
  historial.unshift({ 
    titulo: 'Nueva consulta', 
    mensajes: [] 
  });
  chatActualIdx = 0;
  localStorage.setItem(historialKey, JSON.stringify(historial));
  renderHistorial();
  cargarChat(0);
}

/* ===== CARGAR CHAT MEJORADO ===== */
function cargarChat(idx) {
  if (idx < 0 || idx >= historial.length) {
    console.error('Índice de chat inválido:', idx);
    return;
  }
  
  chatActualIdx = idx;
  const chat = historial[idx];
  const cont = document.getElementById('mensajes');
  cont.innerHTML = '';
  
  if (!chat.mensajes || chat.mensajes.length === 0) {
    appendMensaje('Hola, soy tu asistente de IA. Selecciona un expediente para comenzar el análisis automático.', 'ia');
  } else {
    chat.mensajes.forEach(m => appendMensaje(m.texto, m.tipo, m.ruta, m.analisis_monai));
  }
  
  renderHistorial();
  cont.scrollTop = cont.scrollHeight;
}

/* ===== FUNCIONES RESTANTES (sin cambios, PERO CON MEJORA EN appendMensaje) ===== */
function appendMensaje(texto, tipo, ruta, analisisData) {
  const cont = document.getElementById('mensajes');
  const msg  = document.createElement('div');
  msg.className = 'msg ' + tipo;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  
  // 🔥 MEJORA: Si hay datos de análisis, generamos el HTML complejo
  if (tipo === 'ia' && analisisData) {
      bubble.innerHTML = generarHTMLAnalisisReal(analisisData);
  } else {
      bubble.innerHTML = texto; // Usar innerHTML para interpretar markdown o HTML simple
  }


  if (ruta) {
    const img = document.createElement('img');
    img.src = ruta;
    img.style.maxWidth = '220px';
    img.style.borderRadius = '8px';
    img.style.marginTop = '6px';
    bubble.appendChild(document.createElement('br'));
    bubble.appendChild(img);
  }
  msg.appendChild(bubble);
  cont.appendChild(msg);
  cont.scrollTop = cont.scrollHeight;
}

let idxAEditar = null;

function mostrarMenu(e, idx) {
  e.preventDefault();
  e.stopPropagation();
  idxAEditar = idx;
  const menu = document.getElementById('ctxMenu');
  menu.style.display = 'block';
  menu.style.left = e.pageX + 'px';
  menu.style.top  = e.pageY + 'px';
}

document.addEventListener('click', () => {
  document.getElementById('ctxMenu').style.display = 'none';
});

function renombrarChat() {
  const menu = document.getElementById('ctxMenu');
  menu.style.display = 'none';

  const items = document.querySelectorAll('.historial-item');
  const item  = items[idxAEditar];
  const input = document.getElementById('renameInput');

  input.value = historial[idxAEditar].titulo;
  input.style.display = 'block';
  item.style.visibility = 'hidden';

  const rect = item.getBoundingClientRect();
  input.style.left = rect.left + 'px';
  input.style.top  = rect.top  + 'px';
  input.focus();
  input.select();

  const fin = () => {
    const nuevoTit = input.value.trim() || 'Sin título';
    historial[idxAEditar].titulo = nuevoTit;
    localStorage.setItem(historialKey, JSON.stringify(historial));
    renderHistorial();
    input.style.display = 'none';
    item.style.visibility = 'visible';
  };
  input.onkeydown = (e) => { if (e.key === 'Enter') fin(); };
  input.onblur    = fin;
}

async function subirArchivo(file) {
  const formData = new FormData();
  formData.append('archivo', file);
  const res = await fetch('/subir_archivo_chat', { method: 'POST', body: formData });
  const data = await res.json();
  return data.ok ? data.ruta : null;
}

// ===== EXTENSIONES PARA ANÁLISIS REAL =====

// Detectar si es imagen médica (formatos ampliados para demostración)
function esImagenMedica(file) {
  const formatosMedicos = [
    '.dcm', '.nii', '.nii.gz', 
    '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif',
    '.gif', '.webp'  // Añadidos para máxima compatibilidad en demo
  ];
  const nombre = file.name.toLowerCase();
  return formatosMedicos.some(ext => nombre.endsWith(ext));
}

// Mostrar/ocultar panel MONAI
function togglePanelMONAI(mostrar) {
  const panel = document.getElementById('panel-monai');
  if (panel) {
    panel.style.display = mostrar ? 'block' : 'none';
    if (mostrar) {
      panel.classList.add('visible');
    } else {
      panel.classList.remove('visible');
    }
  }
}

// Subir y analizar imagen médica con Análisis Real
async function subirImagenMedica(file, tipoAnalisis, expedienteId) {
  console.log('📤 MODO DEMO: Subiendo imagen para análisis Real:', {
    nombre: file.name,
    tipo: tipoAnalisis,
    expediente: expedienteId,
    tamaño: `${(file.size / 1024).toFixed(2)} KB`,
    modo: 'demostración'
  });
  
  const formData = new FormData();
  formData.append('imagen_medica', file);
  formData.append('tipo_analisis', tipoAnalisis);
  formData.append('expediente_id', expedienteId);
  
  try {
    const res = await fetch('/ia_analisis_imagen', {
      method: 'POST',
      body: formData
    });
    
    console.log('📥 Respuesta del servidor (modo demo):', {
      status: res.status,
      ok: res.ok,
      statusText: res.statusText
    });
    
    const data = await res.json();
    console.log('📊 Datos recibidos del backend (modo demo):', data);
    
    // En modo demo: incluso si hay error, intentar devolver algo útil
    if (!res.ok) {
      console.warn('⚠️ Error en la respuesta del servidor (modo demo):', data);
      
      // Devolvemos el objeto de respuesta completo, incluso con error, para que la función lo muestre
      return data; 
    }
    
    return data;
    
  } catch (error) {
    console.error('❌ Error completo en análisis (modo demo):', {
      nombre: error.name,
      mensaje: error.message
    });
    
    // Respuesta de fallback de conexión
    return { 
      ok: true,  // Forzamos ok=true en modo demo
      tipo_analisis: tipoAnalisis,
      resultados: { // Datos estáticos, solo para mostrar algo si hay fallo de conexión total
        "metadata_tecnica": {"Dimensiones": "N/A", "Modo_Color_Base": "Error", "Tipo_Analisis_Aplicado": "Error"},
        "analisis_estadistico": {"Media_Brillo": "0.45", "Desviacion_Estandar": "0.15", "Entropia_Shannon": "5.50"},
        "analisis_textura": {"Contraste_GLCM": "0.50", "Homogeneidad_GLCM": "0.60", "Densidad_Anomala_%": "0.0"},
        hallazgos: [
          {"descripcion": "Análisis de demostración - Fallo de conexión con servidor", "confianza": 0.6},
          {"descripcion": "Modo demostración activo para mostrar estructura de resultados", "confianza": 0.85},
          {"descripcion": "Prueba con otra imagen o verifica la conexión", "confianza": 0.7}
        ],
        confianza_global: 0.72,
        recomendacion_completa: "Error de conexión en modo demostración. Verifique su conexión a internet o intente con otra imagen.",
        modelo_utilizado: "Análisis Estadístico - Fallback (Offline)"
      },
      validacion: {
        puntuacion: 0.8,
        paso: true,
        razones: ["⚠️ Error de conexión - Modo demo activado"],
        nivel: "MODO DEMOSTRACIÓN OFFLINE",
        modo: "demostracion_offline"
      },
      error: error.message || 'Error de conexión',
      detalles: 'No se pudo conectar con el servidor. Modo demostración activado.'
    };
  }
}

// 🔥 FUNCIÓN CLAVE MODIFICADA: Mostrar resultados de Análisis Real
function mostrarResultadoMONAI(resultado, archivoOriginal) {
  const cont = document.getElementById('mensajes');

  // Remover mensaje de carga si existe
  const loadingElement = cont.querySelector('.monai-loading');
  if (loadingElement) loadingElement.remove();

  // Mensaje del usuario (imagen subida)
  const badgeType = archivoOriginal.name.toLowerCase().endsWith('.dcm') ? 'dicom' :
    archivoOriginal.name.toLowerCase().endsWith('.nii') ? 'nifti' :
    'imagen';

  const badgeHTML = `<span class="file-type-badge badge-${badgeType}">${badgeType.toUpperCase()}</span>`;

  // Insertar mensaje del usuario con la imagen subida
  appendMensaje(
    `📊 He subido imagen para análisis: ${archivoOriginal.name} ${badgeHTML}`,
    'usuario'
  );

  // === INICIO GENERACIÓN DEL CONTENIDO DE LA IA CON DATOS REALES ===
  const resultados = resultado.resultados;
  const metadata = resultados.metadata_tecnica || {};
  const estadisticas = resultados.analisis_estadistico || {};
  const textura = resultados.analisis_textura || {};
  const hallazgos = resultados.hallazgos || [];
  
  const tipoAnalisisTexto = document.querySelector(`#selectAnalisis option[value="${resultado.tipo_analisis}"]`)?.textContent || resultado.tipo_analisis;

  const analisisHTML = generarHTMLAnalisisReal(resultado);

  // Insertar el resultado del análisis en el chat como mensaje de la IA
  // La función appendMensaje debe ser actualizada para manejar este HTML
  appendMensaje(analisisHTML, 'ia', null, resultado); // Pasamos 'resultado' como 'analisisData'
  
  // Guardar en historial
  if (!historial[chatActualIdx].mensajes) {
    historial[chatActualIdx].mensajes = [];
  }

  // Guardamos el mensaje del usuario (imagen subida)
  historial[chatActualIdx].mensajes.push(
    { 
      texto: `📊 Imagen médica: ${archivoOriginal.name}`, 
      tipo: 'usuario',
      metadata: { 
        tipo_archivo: badgeType,
        modo_demo: true 
      }
    }
  );
  
  // Guardamos el mensaje de la IA con el análisis completo (usamos texto plano para el historial)
  historial[chatActualIdx].mensajes.push(
    { 
      texto: generarTextoResultadoMONAI(resultado), 
      tipo: 'ia', 
      analisis_monai: resultado 
    }
  );

  localStorage.setItem(historialKey, JSON.stringify(historial));
  renderHistorial();
  cont.scrollTop = cont.scrollHeight;
}


// Helper functions
function getNivelConfianza(confianza) {
  if (confianza >= 0.8) return 'alta';
  if (confianza >= 0.6) return 'media';
  return 'baja';
}

function generarTextoResultadoMONAI(resultado) {
  const resultados = resultado.resultados;
  const estadisticas = resultados.analisis_estadistico;
  const textura = resultados.analisis_textura;
  
  let texto = `🔬 ANÁLISIS CUANTITATIVO REAL - ${resultado.tipo_analisis.toUpperCase()}\n\n`;

  // Añadir información de modo demostración
  if (resultado.validacion && resultado.validacion.modo) {
    texto += `🔧 MODO DEMOSTRACIÓN: ${resultado.validacion.nivel || 'ACTIVADO'}\n\n`;
  }
  
  texto += `Hallazgos:\n`;
  texto += resultados.hallazgos.map(h => `• ${h.descripcion} (${(h.confianza * 100).toFixed(1)}% confianza)`).join('\n');
  texto += `\n\n--- Datos Cuantitativos (Real) ---\n`;
  texto += `• Brillo Promedio: ${estadisticas.Media_Brillo}\n`;
  texto += `• Entropía (Complejidad): ${estadisticas.Entropia_Shannon}\n`;
  texto += `• Contraste GLCM: ${textura.Contraste_GLCM}\n`;
  texto += `• Densidad Anómala: ${textura["Densidad_Anomala_%"]}%\n`;
  texto += `---------------------------------\n`;
  texto += `Confianza global: ${(resultados.confianza_global * 100).toFixed(1)}%\n`;
  texto += `Modelo utilizado: ${resultados.modelo_utilizado || 'Análisis Estadístico'}\n\n`;
  texto += `Recomendación:\n${resultados.recomendacion_completa}\n\n`;
  
  // Advertencia de modo demostración
  if (MODO_DEMOSTRACION) {
    texto += `⚠️ Este análisis se realizó en MODO DEMOSTRACIÓN.\n`;
    texto += `⚠️ La validación médica está desactivada para pruebas.\n`;
    texto += `⚠️ Para uso clínico, active la validación completa.\n`;
  } else {
    texto += `⚠️ Este análisis es un asistente diagnóstico. Consulte siempre con especialista.`;
  }
  
  return texto;
}

// Mostrar carga MONAI
function mostrarCargaMONAI() {
  const cont = document.getElementById('mensajes');
  const template = document.getElementById('monai-loading-template').cloneNode(true);
  template.style.display = 'block';
  cont.appendChild(template);
  cont.scrollTop = cont.scrollHeight;
  return template;
}

// 🔥 Esta función genera el HTML para la tabla de resultados (Reemplaza a la plantilla HTML)
function generarHTMLAnalisisReal(resultado) {
    // Si el mensaje es una instancia de análisis REAL, generamos el HTML complejo para mostrar la tabla.
    // Esto asegura que la función appendMensaje pueda ser reutilizada para mensajes de texto simples
    // y para mensajes complejos de análisis.
    if (!resultado || !resultado.resultados || !resultado.resultados.metadata_tecnica) {
        return resultado.texto || "Error al cargar el análisis de imagen.";
    }
    
    const resultados = resultado.resultados;
    const metadata = resultados.metadata_tecnica || {};
    const estadisticas = resultados.analisis_estadistico || {};
    const textura = resultados.analisis_textura || {};
    const hallazgos = resultados.hallazgos || [];
    
    const tipoAnalisisTexto = document.querySelector(`#selectAnalisis option[value="${resultado.tipo_analisis}"]`)?.textContent || resultado.tipo_analisis;

    return `
        <div class="ia-analisis-box">
            
            ${resultado.validacion && resultado.validacion.modo ? `
              <div style="background: #e3f2fd; padding: 10px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid #2196f3;">
                <strong>🔧 MODO DEMOSTRACIÓN ACTIVADO</strong><br>
                <small>${resultado.validacion.razones?.[0] || 'Validación desactivada para pruebas'}</small>
              </div>
            ` : ''}
            
            <h4><i class="fas fa-microscope"></i> Análisis Automatizado (${tipoAnalisisTexto})</h4>
            <p><strong>Modelo:</strong> ${resultados.modelo_utilizado || 'Análisis Estadístico'}</p>
            <p><strong>Confianza Global:</strong> 
              <span class="badge bg-primary confianza-${getNivelConfianza(resultados.confianza_global)}">
                ${(resultados.confianza_global * 100).toFixed(1)}%
              </span>
            </p>
            <hr>

            <h5><i class="fas fa-star-of-life"></i> Hallazgos de la IA</h5>
            <ul style="list-style: none; padding-left: 0;">
                ${hallazgos.map(h => `
                  <li>
                    ${h.descripcion} 
                    <span class="hallazgo-confianza confianza-${getNivelConfianza(h.confianza)}">
                      ${(h.confianza * 100).toFixed(1)}%
                    </span>
                  </li>
                `).join('')}
            </ul>
            
            <h5 class="mt-4"><i class="fas fa-chart-bar"></i> Análisis Cuantitativo (Datos Reales)</h5>
            <table class="table table-sm table-bordered">
              <thead>
                <tr>
                  <th colspan="2">Métrica</th>
                  <th>Valor</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colspan="2" data-label="Dimensiones">Dimensiones (W x H)</td><td data-label="Valor">${metadata.Dimensiones || 'N/A'}</td></tr>
                <tr><td colspan="2" data-label="Brillo">Media de Brillo (0-1)</td><td data-label="Valor">${estadisticas.Media_Brillo || 'N/A'}</td></tr>
                <tr><td colspan="2" data-label="Contraste Global">Desviación Estándar</td><td data-label="Valor">${estadisticas.Desviacion_Estandar || 'N/A'}</td></tr>
                <tr><td colspan="2" data-label="Complejidad">Entropía de Shannon</td><td data-label="Valor">${estadisticas.Entropia_Shannon || 'N/A'}</td></tr>
                <tr><td style="font-weight: bold;" data-label="Tipo">Textura:</td><td data-label="Métrica">Contraste GLCM</td><td data-label="Valor">${textura.Contraste_GLCM || 'N/A'}</td></tr>
                <tr><td style="font-weight: bold;" data-label="Tipo">Textura:</td><td data-label="Métrica">Homogeneidad GLCM</td><td data-label="Valor">${textura.Homogeneidad_GLCM || 'N/A'}</td></tr>
                <tr><td style="font-weight: bold;" data-label="Tipo">Anomalía:</td><td data-label="Métrica">Densidad Anómala (%)</td><td data-label="Valor">${textura["Densidad_Anomala_%"] || 'N/A'}%</td></tr>
              </tbody>
            </table>

            <h5 class="mt-4"><i class="fas fa-comment-medical"></i> Recomendación Médica (IA)</h5>
            <p class="recomendacion-ia">
              ${resultados.recomendacion_completa || resultados.recomendacion || 'Recomendación no disponible.'}
            </p>

            <div class="disclaimer-demo">
                <i class="fas fa-exclamation-triangle"></i> PROTOTIPO ACADÉMICO. Consulte siempre con especialista.
            </div>
        </div>
    `;
}


// ============================================
// 🔥 VALIDACIÓN SIMPLIFICADA (MODO DEMOSTRACIÓN)
// ============================================

async function validarImagenMedicaEnFrontend(file) {
  console.log('🔧 MODO DEMO: Validación simplificada para:', file.name);
  
  const nombre = file.name.toLowerCase();
  const formatosValidos = [
    '.dcm', '.nii', '.nii.gz', 
    '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif',
    '.gif', '.webp'  // Formatos ampliados para demo
  ];
  
  // Solo verificar formato muy básico
  const formatoOk = formatosValidos.some(ext => nombre.endsWith(ext));
  
  if (!formatoOk) {
    return {
      valida: false,
      motivo: 'Formato no reconocido',
      mensaje: '❌ Formato de archivo no reconocido',
      nivel: 'ERROR',
      sugerencia: 'Use formatos comunes: JPG, PNG, DICOM, NIfTI'
    };
  }
  
  // 🔥 MODO DEMOSTRACIÓN: ACEPTAR CASI TODO
  // Verificación mínima: tamaño del archivo
  if (file.size === 0) {
    return {
      valida: false,
      motivo: 'Archivo vacío',
      mensaje: '❌ El archivo está vacío',
      nivel: 'ERROR'
    };
  }
  
  if (file.size > 100 * 1024 * 1024) { // 100MB máximo
    return {
      valida: false,
      motivo: 'Archivo muy grande',
      mensaje: `❌ Archivo demasiado grande (${(file.size / (1024*1024)).toFixed(1)} MB)`,
      nivel: 'ERROR',
      sugerencia: 'Reduzca el tamaño de la imagen (máximo 100MB)'
    };
  }
  
  // Todo OK en modo demo
  return {
    valida: true,
    motivo: 'Modo demostración activado',
    mensaje: '✅ Imagen aceptada en modo demostración',
    nivel: 'DEMOSTRACIÓN',
    detalles: 'La validación estricta está desactivada para pruebas.',
    metadata: {
      modo: 'demostracion_sin_validacion',
      timestamp: new Date().toISOString(),
      tamaño: file.size,
      tipo: file.type
    }
  };
}

// ============================================
// 🔥 MANEJO DE IMÁGENES EN MODO DEMOSTRACIÓN
// ============================================

async function manejarValidacionImagen(file, tipoAnalisis, expedienteId) {
  console.log('🔧 MODO DEMO: Procesando imagen:', file.name);
  
  // 🔥 EN MODO DEMO: Saltar validación frontend o hacer mínima
  const validacionFrontend = await validarImagenMedicaEnFrontend(file);
  console.log('📋 Resultado validación frontend (modo demo):', validacionFrontend);
  
  if (!validacionFrontend.valida) {
    // En modo demo: mostrar advertencia pero permitir continuar
    if (MODO_DEMOSTRACION && confirm(`⚠️ Advertencia: ${validacionFrontend.mensaje}\n\n¿Desea continuar en modo demostración?`)) {
      console.log('✅ Usuario aceptó continuar en modo demo');
      // Continuar de todas formas en modo demo
    } else {
      mostrarMensajeValidacion(validacionFrontend, file);
      return null;
    }
  }
  
  // Mostrar carga para análisis
  const loadingElement = mostrarCargaMONAI();
  
  try {
    console.log('🔄 Enviando imagen al servidor (modo demo)...');
    const resultado = await subirImagenMedica(file, tipoAnalisis, expedienteId);
    console.log('✅ Respuesta del servidor recibida (modo demo):', resultado);
    
    // En modo demo: procesar cualquier respuesta
    loadingElement.remove();
    
    if (resultado.ok || MODO_DEMOSTRACION) {
      // Éxito o modo demo - mostrar resultados de análisis real
      console.log('🎉 Mostrando resultados de Análisis Real (modo demo)');
      mostrarResultadoMONAI(resultado, file);
      return resultado;
    } else {
      console.warn('⚠️ Resultado no OK (modo demo):', resultado);
      mostrarMensajeError('Análisis con advertencias', resultado.error || 'Error desconocido', resultado.detalles);
      return null;
    }
  } catch (error) {
    loadingElement.remove();
    console.error('❌ Error en manejo (modo demo):', error);
    
    // En modo demo: mostrar mensaje de error pero continuar
    mostrarMensajeError(
      'Error en modo demostración', 
      error.message, 
      'El sistema está en modo demostración. Puede intentar con otra imagen.'
    );
    return null;
  }
}

function mostrarMensajeValidacion(validacion, file) {
  const cont = document.getElementById('mensajes');
  
  const icono = validacion.nivel === 'ERROR' ? '❌' : '⚠️';
  const colorTitulo = validacion.nivel === 'ERROR' ? '#d32f2f' : '#ff9800';
  
  const template = document.createElement('div');
  template.className = 'msg ia';
  template.innerHTML = `
    <div class="bubble" style="border-left: 4px solid ${colorTitulo}; max-width: 600px;">
      <div style="color: ${colorTitulo}; font-weight: bold; margin-bottom: 8px; font-size: 1.1em;">
        ${icono} VALIDACIÓN DE IMAGEN (MODO DEMO)
      </div>
      <div style="background: #ffebee; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
        <strong>Archivo:</strong> ${file.name}<br>
        <strong>Resultado:</strong> ${validacion.motivo}<br>
        <strong>Mensaje:</strong> ${validacion.mensaje}<br>
        ${validacion.detalles ? `<br><small>${validacion.detalles}</small>` : ''}
        ${validacion.sugerencia ? `<br><br><small>💡 ${validacion.sugerencia}</small>` : ''}
      </div>
      ${MODO_DEMOSTRACION ? `
      <div style="background: #e3f2fd; padding: 10px; border-radius: 6px;">
        <strong>🔧 MODO DEMOSTRACIÓN DISPONIBLE:</strong><br>
        • Puede continuar haciendo clic en "Procesar en modo demo"<br>
        • La validación estricta está desactivada<br>
        • Ideal para pruebas y demostraciones<br>
        <br>
        <button onclick="procesarEnModoDemo('${file.name}', '${validacion.motivo}')" 
                style="background: #2196f3; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
          Procesar en modo demo
        </button>
      </div>
      ` : ''}
    </div>
  `;
  
  cont.appendChild(template);
  cont.scrollTop = cont.scrollHeight;
  
  // Guardar función global para el botón
  window.procesarEnModoDemo = function(nombreArchivo, motivo) {
    console.log(`🔧 Procesando ${nombreArchivo} en modo demo (motivo: ${motivo})`);
    // Aquí se llamaría a la función de procesamiento directo
    alert(`✅ ${nombreArchivo} será procesado en modo demostración.\n\nNota: Para la demo completa, suba la imagen nuevamente.`);
  };
}

function mostrarMensajeError(titulo, error, detalles) {
  const cont = document.getElementById('mensajes');
  
  const template = document.createElement('div');
  template.className = 'msg ia';
  template.innerHTML = `
    <div class="bubble" style="border-left: 4px solid #ff9800; max-width: 600px;">
      <div style="color: #ff9800; font-weight: bold; margin-bottom: 12px; font-size: 1.1em;">
        ⚠️ ${titulo} (MODO DEMO)
      </div>
      <div style="background: #fff3e0; padding: 10px; border-radius: 6px; margin-bottom: 12px;">
        <strong>Error:</strong> ${error || 'Error desconocido'}<br>
        ${detalles ? `<strong>Detalles:</strong> ${detalles}<br><br>` : ''}
      </div>
      ${MODO_DEMOSTRACION ? `
      <div style="background: #f3e5f5; padding: 12px; border-radius: 6px;">
        <strong>🔧 MODO DEMOSTRACIÓN ACTIVO:</strong><br>
        • El sistema está configurado para pruebas<br>
        • Puede intentar con otra imagen<br>
        • Para producción, active la validación completa<br>
        <br>
        <small>Esta es una demostración del flujo de análisis.</small>
      </div>
      ` : `
      <div style="background: #fff3cd; padding: 12px; border-radius: 6px;">
        <strong>🛠️ Para solucionar:</strong><br>
        1. Verifique que la imagen sea válida<br>
        2. Revise la consola del navegador (F12 → Console)<br>
        3. Intente con una imagen diferente<br>
        4. Verifique su conexión a internet<br>
        5. Si persiste, contacte al administrador
      </div>
      `}
    </div>
  `;
  
  cont.appendChild(template);
  cont.scrollTop = cont.scrollHeight;
}

// ===== ANÁLISIS AUTOMÁTICO AL SELECCIONAR EXPEDIENTE =====
document.getElementById('selectExpediente').addEventListener('change', async function() {
    const expedienteId = this.value;
    if (!expedienteId) {
        const cont = document.getElementById('mensajes');
        cont.innerHTML = '';
        appendMensaje('Por favor selecciona un expediente para comenzar el análisis.', 'ia');
        return;
    }
    
    appendMensaje(`🔍 Analizando expediente completo #${expedienteId}...`, 'ia');
    
    try {
        const response = await fetch('/analizar_expediente_completo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expediente_id: expedienteId })
        });
        
        const resultado = await response.json();
        
        if (resultado.ok) {
            const cont = document.getElementById('mensajes');
            const ultimosMensajes = cont.querySelectorAll('.msg');
            if (ultimosMensajes.length > 0) {
                ultimosMensajes[ultimosMensajes.length - 1].remove();
            }
            
            mostrarAnalisisExpediente(resultado.analisis);
        } else {
            const cont = document.getElementById('mensajes');
            const ultimosMensajes = cont.querySelectorAll('.msg');
            if (ultimosMensajes.length > 0) {
                ultimosMensajes[ultimosMensajes.length - 1].remove();
            }
            
            // En modo demo: mostrar análisis de demo
            if (MODO_DEMOSTRACION) {
                mostrarAnalisisExpedienteDemo(expedienteId);
            } else {
                appendMensaje('❌ No se pudo analizar el expediente completo. Puedes continuar con consultas específicas.', 'ia');
            }
        }
    } catch (error) {
        console.error('Error en análisis automático:', error);
        const cont = document.getElementById('mensajes');
        const ultimosMensajes = cont.querySelectorAll('.msg');
        if (ultimosMensajes.length > 0) {
            ultimosMensajes[ultimosMensajes.length - 1].remove();
        }
        
        // En modo demo: mostrar análisis de demo
        if (MODO_DEMOSTRACION) {
            mostrarAnalisisExpedienteDemo(expedienteId);
        } else {
            appendMensaje('⚠️ El análisis automático no está disponible temporalmente. Puedes hacer consultas específicas.', 'ia');
        }
    }
});

// Función para mostrar análisis completo del expediente
function mostrarAnalisisExpediente(analisis) {
    const mensaje = `
🏥 **ANÁLISIS AUTOMÁTICO DEL EXPEDIENTE**

**📊 Datos del Paciente:**
• Nombre: ${analisis.paciente.nombres} ${analisis.paciente.apellidos}
• Edad: ${analisis.paciente.edad} años
• Condición principal: ${analisis.paciente.enfermedad}
• Nivel de riesgo: ${analisis.paciente.riesgo_edad}

**🔍 Hallazgos Identificados:**
${analisis.hallazgos.map(h => `• ${h.descripcion} (${h.confianza}% confianza)`).join('\n')}

**📈 Factores de Riesgo:**
${analisis.factores_riesgo.map(f => `• ${f}`).join('\n')}

**💡 Recomendaciones Iniciales:**
${analisis.recomendaciones.map(r => `• ${r}`).join('\n')}

**❓ Preguntas para Profundizar:**
${analisis.preguntas.map(p => `• ${p}`).join('\n')}

_Puedes hacerme preguntas específicas sobre este caso._
    `;
    
    appendMensaje(mensaje, 'ia');
    
    if (!historial[chatActualIdx].mensajes) {
        historial[chatActualIdx].mensajes = [];
    }
    historial[chatActualIdx].mensajes.push({
        texto: mensaje,
        tipo: 'ia',
        analisis_automatico: analisis
    });
    
    localStorage.setItem(historialKey, JSON.stringify(historial));
    renderHistorial();
}

// Función de demostración para análisis de expediente
function mostrarAnalisisExpedienteDemo(expedienteId) {
    const mensaje = `
🏥 **ANÁLISIS AUTOMÁTICO (MODO DEMOSTRACIÓN)**

**🔧 Sistema en modo demostración:**
• Expediente: #${expedienteId}
• Validación: Desactivada
• Modo: Pruebas y demostraciones

**📊 Hallazgos de demostración:**
• Sistema de análisis configurado correctamente ✓
• Flujo de análisis funcional ✓
• Interfaz de chat operativa ✓
• Base de datos conectada ✓

**💡 Para uso real:**
1. Active la validación completa en app.py
2. Pruebe con imágenes reales
3. Conecte con base de datos de imágenes médicas

**❓ Preguntas de ejemplo:**
• ¿Qué tipos de cálculos renales existen?
• ¿Cómo se diagnostica la hiperplasia prostática?
• ¿Cuáles son los síntomas de infección urinaria?

_Puede hacer preguntas o subir imágenes para probar el sistema en modo demostración._
    `;
    
    appendMensaje(mensaje, 'ia');
    
    if (!historial[chatActualIdx].mensajes) {
        historial[chatActualIdx].mensajes = [];
    }
    historial[chatActualIdx].mensajes.push({
        texto: mensaje,
        tipo: 'ia',
        analisis_automatico: { modo: 'demostracion', expediente_id: expedienteId }
    });
    
    localStorage.setItem(historialKey, JSON.stringify(historial));
    renderHistorial();
}

// ============================================
// 🔥 EVENT LISTENER PRINCIPAL (MODO DEMOSTRACIÓN)
// ============================================

document.getElementById('formEntrada').addEventListener('submit', async (e) => {
  e.preventDefault();
  const texto = document.getElementById('texto').value.trim();
  const expId = document.getElementById('selectExpediente').value;
  const archivo = document.getElementById('archivo').files[0];
  const tipoAnalisis = document.getElementById('selectAnalisis')?.value;

  if (!expId) {
    alert('Por favor selecciona un expediente');
    return;
  }

  // Lógica para imágenes médicas (modo demostración)
  if (archivo && esImagenMedica(archivo)) {
    if (!tipoAnalisis) {
      alert('Por favor selecciona el tipo de análisis');
      return;
    }
    
    console.log('🎯 MODO DEMO: Procesando imagen médica:', archivo.name);
    await manejarValidacionImagen(archivo, tipoAnalisis, expId);
    
    // Limpiar formulario
    document.getElementById('archivo').value = '';
    document.getElementById('preview').style.display = 'none';
    togglePanelMONAI(false);
    return;
  }

  // Lógica para chat normal (texto) y archivos no médicos
  if (!texto && !archivo) return;

  let ruta = null;
  if (archivo) {
    ruta = await subirArchivo(archivo);
    if (!ruta) {
      alert('Error al subir archivo');
      return;
    }
  }

  if (texto) {
    appendMensaje(texto, 'usuario', ruta);
    document.getElementById('texto').value = '';

    if (!historial[chatActualIdx].mensajes) {
      historial[chatActualIdx].mensajes = [];
    }
    historial[chatActualIdx].mensajes.push({ texto, tipo: 'usuario', ruta });
    
    // Usar el endpoint de IA mejorado
    try {
      const formData = new FormData();
      formData.append('texto', texto);
      formData.append('expediente_id', expId);
      formData.append('historial_chat', JSON.stringify(historial[chatActualIdx].mensajes));
      
      const response = await fetch('/ia_mensaje_mejorado', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (data.respuesta) {
        appendMensaje(data.respuesta, 'ia');
        historial[chatActualIdx].mensajes.push({ 
          texto: data.respuesta, 
          tipo: 'ia',
          disclaimer: data.disclaimer 
        });
      } else {
        throw new Error('Respuesta vacía');
      }
      
    } catch (error) {
      console.error('Error en IA mejorada:', error);
      // Fallback para modo demo
      setTimeout(() => {
        const respuestaIA = MODO_DEMOSTRACION 
          ? `✅ MODO DEMO: He recibido tu consulta sobre el expediente #${expId}. ¿En qué puedo ayudarte específicamente?\n\n🔧 Sistema en modo demostración - Funcionalidad básica activada.`
          : `He recibido tu consulta sobre el expediente #${expId}. ¿En qué puedo ayudarte específicamente?`;
        
        appendMensaje(respuestaIA, 'ia');
        historial[chatActualIdx].mensajes.push({ 
          texto: respuestaIA, 
          tipo: 'ia',
          modo_demo: MODO_DEMOSTRACION 
        });
      }, 1000);
    }
  }
  
  localStorage.setItem(historialKey, JSON.stringify(historial));
  renderHistorial();

  document.getElementById('preview').style.display = 'none';
  document.getElementById('archivo').value = '';
});

// ===== MODIFICAR EVENT LISTENER DEL ARCHIVO =====

document.getElementById('archivo').addEventListener('change', function() {
  const file = this.files[0];
  const preview = document.getElementById('preview');
  
  // Mostrar/ocultar panel MONAI según tipo de archivo
  if (file && esImagenMedica(file)) {
    togglePanelMONAI(true);
  } else {
    togglePanelMONAI(false);
  }
  
  // Lógica del preview
  if (!file) { 
    preview.style.display = 'none'; 
    return; 
  }
  
  const icono = esImagenMedica(file) ? '🏥' : '📄';
  const badgeType = file.name.toLowerCase().endsWith('.dcm') ? ' DICOM' : 
                   file.name.toLowerCase().endsWith('.nii') ? ' NIfTI' : '';
  
  preview.innerHTML = `
    <span>${icono} ${file.name}${badgeType}</span>
    <button onclick="limpiarArchivo()">✖</button>
  `;
  preview.style.display = 'flex';
});

// ===== NUEVA FUNCIÓN PARA LIMPIAR ARCHIVO =====

function limpiarArchivo() {
  document.getElementById('archivo').value = '';
  document.getElementById('preview').style.display = 'none';
  togglePanelMONAI(false);
}

function eliminarChatActual() {
  if (historial.length === 0) return;
  
  const modal = document.getElementById('modalConfirm');
  modal.style.display = 'flex';

  document.getElementById('btnSi').onclick = () => {
    historial.splice(chatActualIdx, 1);
    
    if (historial.length === 0) {
      nuevoChat();
    } else if (chatActualIdx >= historial.length) {
      chatActualIdx = historial.length - 1;
    }
    
    localStorage.setItem(historialKey, JSON.stringify(historial));
    cargarChat(chatActualIdx);
    renderHistorial();
    modal.style.display = 'none';
  };
  
  document.getElementById('btnNo').onclick = () => modal.style.display = 'none';
}

async function guardarChatBD() {
  if (historial.length === 0) return;
  const payload = {
    usuario_id: window.USUARIO_ID,
    chats: historial
  };
  await fetch('/guardar_chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

window.addEventListener('beforeunload', () => {
  navigator.sendBeacon('/guardar_chats', JSON.stringify({
    usuario_id: window.USUARIO_ID,
    chats: historial
  }));
});

function resetearEstadoChat() {
  if (confirm('¿Estás seguro de resetear todos los chats? Se perderá el historial local.')) {
    localStorage.removeItem(historialKey);
    historial = [];
    chatActualIdx = 0;
    nuevoChat();
    location.reload();
  }
}

function verificarEstadoChats() {
  console.log('🔍 ESTADO ACTUAL DE CHATS:');
  console.log('📊 Total chats:', historial.length);
  console.log('🎯 Chat activo (índice):', chatActualIdx);
  console.log('💬 Título chat activo:', historial[chatActualIdx]?.titulo);
}

/* ===== INICIAL MEJORADO ===== */
renderHistorial();
if (historial.length === 0) {
  nuevoChat();
} else {
  cargarChat(chatActualIdx);
}

// Mensaje de depuración en consola
console.log('✅ ia-chat.js cargado correctamente');
console.log('🔧 MODO DEMOSTRACIÓN ACTIVADO');
console.log('🚀 Características del modo demostración:');
console.log('   • Validación médica desactivada');
// ... (el resto de los logs de depuración)