import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

// Landscape A4: 841 x 595 pt
const PW = 841; const PH = 595; const M = 26; const CW = PW - M * 2;

const C = {
  // Colores suaves "Eco-Ink"
  verdeOsc:  [46,  125, 50]  as [number,number,number],
  verdeAcc:  [67,  160, 71]  as [number,number,number],
  verdeTint: [241, 248, 233] as [number,number,number],
  azulAcc:   [25,  118, 210] as [number,number,number],
  azulTint:  [227, 242, 253] as [number,number,number],
  ambarAcc:  [245, 124, 0]   as [number,number,number],
  ambarTint: [255, 243, 224] as [number,number,number],
  gris50:    [250, 250, 250] as [number,number,number],
  gris100:   [245, 245, 245] as [number,number,number],
  gris300:   [210, 210, 210] as [number,number,number],
  gris500:   [140, 140, 140] as [number,number,number],
  label:     [50,  50,  50]  as [number,number,number],
  negro:     [20,  20,  20]  as [number,number,number],
  blanco:    [255, 255, 255] as [number,number,number],
};

const CULTIVOS_A = ['Pasto mejorado','Pasto no mejorado','Cebolla','Papas','Cebada','Trigo','Maíz','Habas','Hortalizas','Fríjol','Flores'];
const CULTIVOS_B = ['Frutales','Melloco','Chocho','Quinua','Baldío','Monte','Bosque','Otros'];
const ANIMALES_MENORES = ['Cuyes / Conejos','Pollos de engorde','Gallinas ponedoras','Gallinas de campo','Ovejas / Cabras','Porcino (Chanchos)'];
const GANADO = ['Vacas en producción','Vacas secas','Vaconas','Terneras','Terneros','Toretes','Toros','Equinos'];

async function loadImgBase64(url: string): Promise<string> {
  try {
    const r = await fetch(url);
    const blob = await r.blob();
    return new Promise((res) => {
      const reader = new FileReader();
      reader.onloadend = () => res(reader.result as string);
      reader.readAsDataURL(blob);
    });
  } catch { return ''; }
}

function addHeader(doc: jsPDF, logoIzq: string, logoDer: string) {
  doc.setFillColor(...C.blanco);
  doc.rect(0, 0, PW, 40, 'F');

  if (logoIzq) {
    try {
      const props = doc.getImageProperties(logoIzq);
      const ratio = props.width / props.height;
      const h = 28; const w = h * ratio;
      doc.addImage(logoIzq, 'PNG', M, 6, w, h);
    } catch(_) {}
  }
  if (logoDer) {
    try {
      const props = doc.getImageProperties(logoDer);
      const ratio = props.width / props.height;
      const h = 24; const w = h * ratio;
      doc.addImage(logoDer, 'PNG', PW - M - w, 8, w, h);
    } catch(_) {}
  }

  doc.setFont('helvetica','bold'); doc.setFontSize(12); doc.setTextColor(...C.verdeOsc);
  doc.text('ESTUDIO DEFINITIVO DE PRESA EN EL RÍO POROTOG', PW/2, 18, {align:'center'});
  doc.setFont('helvetica','bold'); doc.setFontSize(8); doc.setTextColor(...C.gris500);
  doc.text('PADRÓN DE USUARIOS · Sistema de Riego Comunitario Guanguilqui Porotog · Provincia Pichincha – Cantón Cayambe', PW/2, 28, {align:'center'});
  
  doc.setDrawColor(...C.verdeAcc); doc.setLineWidth(1); doc.line(M, 38, PW-M, 38);
}

function addFooter(doc: jsPDF, page: number) {
  const y = PH - 16;
  doc.setDrawColor(...C.gris300); doc.setLineWidth(0.3); doc.line(M, y, PW-M, y);
  
  doc.setFont('helvetica','normal'); doc.setFontSize(7); doc.setTextColor(...C.gris500);
  doc.text(`Hoja ${page} de 2`, PW-M, y+9, {align:'right'});
}

function secBar(doc: jsPDF, x: number, y: number, w: number, titulo: string,
                acc: [number,number,number], tint: [number,number,number]): number {
  doc.setFillColor(...tint);
  doc.rect(x, y, w, 14, 'F');
  doc.setDrawColor(...acc); doc.setLineWidth(1); doc.line(x, y+14, x+w, y+14);
  
  doc.setFont('helvetica','bold'); doc.setFontSize(7.5); doc.setTextColor(...acc);
  doc.text(titulo.toUpperCase(), x+6, y+10);
  doc.setTextColor(...C.negro);
  return y+16;
}

const BASE = {
  theme: 'plain' as const,
  styles: { fontSize:7, cellPadding:{top:2.5,bottom:2.5,left:4,right:4},
    textColor:C.negro, lineColor:C.gris300, lineWidth:0.3 },
  alternateRowStyles: {fillColor: C.blanco},
};

// Generador de tablas de 4 columnas (2 pares de Label-Value) para ahorrar espacio
function tblGen4Col(doc: jsPDF, startY: number, left: number, width: number,
    body: any[][], labelW: number) {
  
  const valW = (width - (labelW * 2)) / 2;

  autoTable(doc, {
    ...BASE, startY,
    margin:{left, right: PW-left-width}, tableWidth: width,
    columnStyles:{
      0:{fontStyle:'bold', textColor:C.label, fillColor:C.gris50, cellWidth:labelW},
      1:{cellWidth:valW},
      2:{fontStyle:'bold', textColor:C.label, fillColor:C.gris50, cellWidth:labelW},
      3:{cellWidth:valW},
    },
    body,
  });
  return (doc as any).lastAutoTable.finalY;
}

export const generateAprobacionVacia = async () => {
  await buildPDF();
};

// Estilo de etiqueta (checkbox)
const cb = (text: string) => `[   ] ${text}`;

async function buildPDF() {
  const [logoIzq, logoDer] = await Promise.all([
    loadImgBase64('/logo-izq.png'),
    loadImgBase64('/logo-der.png'),
  ]);

  const doc = new jsPDF({unit:'pt', format:'a4', orientation:'landscape'});

  // ══ HOJA 1 ══════════════════════════════════════════════════════════════
  addHeader(doc, logoIzq, logoDer);
  let y = 44;

  // ── SECCIÓN 1: PROPIETARIO (4 Columnas) ─────────────────────────────────
  y = secBar(doc, M, y, CW, '1. Datos del Propietario', C.verdeAcc, C.blanco);
  y = tblGen4Col(doc, y, M, CW, [
    ['Clave Catastral', '', 'Cédula de Identidad', ''],
    ['Apellidos', '', 'Nombres', ''],
    ['Parroquia', `${cb('CANGAHUA')}   ${cb('OTÓN')}   ${cb('CUSUBAMBA')}   ${cb('ASCÁZUBI')}`, 'Comunidad', ''],
    ['Teléfono Celular', '', 'Teléfono Casa', ''],
    ['Hijos Hombres / Mujeres', 'Hombres: _______   Mujeres: _______', 'Tenencia del Predio', `${cb('Escritura')}     ${cb('Sin Escritura')}`],
    ['Sector', `${cb('Porotog')}   ${cb('Guanguilqui')}   ${cb('Guang-Portog')}`, 'Nivel de Instrucción', `${cb('Ninguno')}  ${cb('Alfab.')}  ${cb('Prim.')}  ${cb('Sec.')}  ${cb('Sup.')}`],
  ], 120);

  y += 6;

  // ── SECCIÓN 2: PREDIO Y RIEGO (4 Columnas) ──────────────────────────────
  y = secBar(doc, M, y, CW, '2. Datos del Predio (UPA) y Riego', C.verdeAcc, C.blanco);
  y = tblGen4Col(doc, y, M, CW, [
    ['Organización de Riego', '', 'Código del Predio', ''],
    ['Sector dentro la Comunidad', '', 'N° Predio', ''],
    ['Canal (Nombre)', '', 'Caudal (litros/segundo)', `_______ l/s   ${cb('Recibe la Comunidad')}   ${cb('Recibe individual')}`],
    ['Área Total (m2/Ha)', '', 'Área con Riego (m2/Ha)', ''],
    ['Área sin Riego (m2/Ha)', '', 'Frecuencia de Riego', `${cb('Perm.')}   ${cb('Mens.')}   ${cb('Quin.')}   ${cb('Sem.')}   ${cb('No tiene')}`],
    ['Método de Riego %', 'Gravedad:_______%    Asp:_______%    Goteo:_______%', 'N° Días / Horas Turno', 'Días: _______    Horas Turno: _______'],
    ['Valor Tarifa ($)', `$_________     ${cb('turno')}   ${cb('fijo mes')}   ${cb('fijo anual')}   ${cb('x Ha.')}`, '¿Tiene reservorio?', `${cb('Privado')}   ${cb('Comunitario')}   ${cb('No')}`],
  ], 120);

  y += 6;

  // ── SECCIÓN 3: SERVICIOS Y UBICACIÓN (4 Columnas) ───────────────────────
  y = secBar(doc, M, y, CW, '3. Servicios y Ubicación', C.azulAcc, C.blanco);
  y = tblGen4Col(doc, y, M, CW, [
    ['Agua Consumo Humano', `${cb('SÍ')}     ${cb('NO')}`, 'Energía Eléctrica', `${cb('SÍ')}     ${cb('NO')}`],
    ['Material Construcción', `${cb('HORMIGÓN ARMADO')}   ${cb('EST. METÁLICA')}   ${cb('LADRILLO')}\n${cb('BLOQUE')}   ${cb('MADERA')}   ${cb('MIXTA')}   ${cb('Otros')}`, 'COTA (msnm)', ''],
    ['Coordenada X (UTM)', '', 'Coordenada Y (UTM)', ''],
  ], 120);

  y += 6;

  // ── SECCIÓN 4: PRODUCCIÓN (4 Tablas contiguas) ──────────────────────────
  y = secBar(doc, M, y, CW, '4. Sistema de Producción Agrícola y Pecuario', C.ambarAcc, C.blanco);

  const wAgri = Math.floor(CW * 0.51);
  const wPecu = CW - wAgri - 8;

  const CULTIVOS = [...CULTIVOS_A, ...CULTIVOS_B];
  const ANIMALES = [...ANIMALES_MENORES, ...GANADO];
  
  const cAgri = M;
  const cPecu = M + wAgri + 8;

  const pageNum = doc.getCurrentPageInfo().pageNumber;

  autoTable(doc, {...BASE, startY:y,
    margin:{left:cAgri, right:PW-cAgri-wAgri}, tableWidth:wAgri,
    head:[['Cultivos','Superficie','Principal','Autoconsumo','Mercado','Agroindustria','Exportación']],
    headStyles:{fillColor:C.ambarTint,textColor:C.ambarAcc,fontStyle:'bold',fontSize:5.2,lineColor:C.gris300,lineWidth:0.3, halign:'center'},
    columnStyles:{
      0:{cellWidth:95,fontSize:6},
      1:{cellWidth:48,halign:'center'},
      2:{cellWidth:46,halign:'center'},
      3:{cellWidth:58,halign:'center'},
      4:{cellWidth:40,halign:'center'},
      5:{cellWidth:63,halign:'center'},
      6:{cellWidth:52,halign:'center'}
    },
    styles: {...BASE.styles, cellPadding: 1.5, fontSize: 5.5, overflow: 'hidden'},
    body: CULTIVOS.map(c=>[c, '', '', '', '', '', ''])
  });
  const yA_ = (doc as any).lastAutoTable.finalY;

  // Forzar que la segunda tabla se dibuje en la misma página donde empezó la primera
  doc.setPage(pageNum);

  autoTable(doc, {...BASE, startY:y,
    margin:{left:cPecu, right:PW-cPecu-wPecu}, tableWidth:wPecu,
    head:[['Animales / Especie','Cantidad','Autoconsumo','Mercado','Agroindustria','Exportación']],
    headStyles:{fillColor:C.ambarTint,textColor:C.ambarAcc,fontStyle:'bold',fontSize:5.2,lineColor:C.gris300,lineWidth:0.3, halign:'center'},
    columnStyles:{
      0:{cellWidth:100,fontSize:6},
      1:{cellWidth:43,halign:'center'},
      2:{cellWidth:60,halign:'center'},
      3:{cellWidth:43,halign:'center'},
      4:{cellWidth:70,halign:'center'},
      5:{cellWidth:63,halign:'center'}
    },
    styles: {...BASE.styles, cellPadding: 1.5, fontSize: 5.5, overflow: 'hidden'},
    body: ANIMALES.map(a=>[a, '', '', '', '', ''])
  });
  const yB_ = (doc as any).lastAutoTable.finalY;

  // En caso de que se haya creado una página nueva por el tamaño, nos movemos a la última página para seguir
  const finalPage = Math.max(
    (doc as any).lastAutoTable.pageNumber || pageNum,
    pageNum
  );
  doc.setPage(finalPage);

  y = Math.max(yA_, yB_) + 2;

  autoTable(doc, {...BASE, startY:y,
    margin:{left:M, right:PW-M-CW}, tableWidth:CW,
    columnStyles:{
      0:{fontStyle:'bold',textColor:C.label,fillColor:C.gris50,cellWidth:90},
      2:{fontStyle:'bold',textColor:C.label,fillColor:C.gris50,cellWidth:110},
    },
    body:[
      ['Uso del Agua', 'Soberanía Alimentaria: _______%     Act. Productivas: _______%', 'Actividad Productiva', `${cb('Particular')}     ${cb('Empresarial')}`],
    ]});

  addFooter(doc, 1);

  // ══ HOJA 2 ══════════════════════════════════════════════════════════════
  doc.addPage();
  addHeader(doc, logoIzq, logoDer);
  y = 44;

  y = secBar(doc, M, y, CW, '5. Datos de la Comunidad y Conocimiento de la Junta de Agua', C.verdeAcc, C.blanco);

  // Convertimos a 4 columnas para ahorrar aún más espacio
  y = tblGen4Col(doc, y, M, CW, [
    ['¿La Junta tiene estatutos?',    `${cb('SÍ')}   ${cb('NO')}   ${cb('NSC')}`, '¿La Junta tiene reglamentos?',  `${cb('SÍ')}   ${cb('NO')}   ${cb('NSC')}`],
    ['¿Conoce sobre el Proyecto de la presa Río Porotog?', `${cb('SÍ')}   ${cb('NO')}   ${cb('NSC')}`, {content:'', styles:{fillColor:C.blanco}}, ''],
    [{content:'DATOS DE LA COMUNIDAD', colSpan: 4, styles:{fillColor:C.verdeTint, textColor:C.verdeAcc, halign:'center', fontStyle:'bold'}}],
    ['¿Cómo se elige a la directiva?', '', '¿Cómo se llama el Presidente de la Junta de Agua?', ''],
    ['¿Conoce quién es el operador del sistema en su sector?', '', '¿Cuántos años tiene este sistema de riego?', ''],
    ['¿Conoce cuántos Km tiene el canal principal?', '', '¿Ha recibido capacitación?',    `${cb('SÍ')}   ${cb('NO')}   ${cb('NSC')}`],
    ['¿Le gustaría recibir capacitación?',    `${cb('SÍ')}   ${cb('NO')}   ${cb('NSC')}`, {content:'Temas de capacitación deseados', styles:{fillColor:C.gris50, fontStyle:'bold', textColor:C.label}}, '']
  ], 130);

  y += 6;

  // ── SECCIÓN 6: EMPLAZAMIENTO ────────────────────────────────────────────
  y = secBar(doc, M, y, CW, '6. Emplazamiento – Croquis del Predio', C.gris500, C.blanco);
  const yMax = PH - 40;
  const empH = yMax - y - 30;
  doc.setFillColor(255,255,255); doc.setDrawColor(...C.gris300); doc.setLineWidth(0.3);
  doc.roundedRect(M, y, CW, empH, 2, 2, 'FD');

  doc.setFillColor(220,220,220);
  const gap = 12;
  for (let dx = M+gap; dx < M+CW-4; dx+=gap)
    for (let dy = y+gap; dy < y+empH-4; dy+=gap)
      doc.circle(dx, dy, 0.45, 'F');



  const fRow = y + empH + 6;
  doc.setDrawColor(...C.gris300); doc.setLineWidth(0.3); doc.rect(M, fRow, CW, 18);
  doc.setFillColor(...C.gris50); doc.rect(M, fRow, 140, 18, 'F');
  doc.setFont('helvetica','bold'); doc.setFontSize(7.5); doc.setTextColor(...C.label);
  doc.text('Investigado por:', M+5, fRow+12);
  
  doc.line(M+320, fRow, M+320, fRow+18);
  doc.setFillColor(...C.gris50); doc.rect(M+320, fRow, 50, 18, 'F');
  doc.setFont('helvetica','bold'); doc.setTextColor(...C.label);
  doc.text('Fecha:', M+328, fRow+12);
  
  doc.line(M+470, fRow, M+470, fRow+18);
  doc.setFillColor(...C.gris50); doc.rect(M+470, fRow, 80, 18, 'F');
  doc.setFont('helvetica','bold'); doc.setTextColor(...C.label);
  doc.text('Observaciones:', M+475, fRow+12);

  addFooter(doc, 2);
  doc.save(`Formulario_Aprobacion_Vacio_${new Date().toISOString().split('T')[0]}.pdf`);
}
