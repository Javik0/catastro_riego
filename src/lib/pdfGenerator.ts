import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const VERDE      = [34, 139, 34]   as [number,number,number];
const VERDE_CLR  = [213, 237, 213] as [number,number,number];
const VERDE_MED  = [101, 163, 101] as [number,number,number];
const GRIS_CLR   = [245, 246, 246] as [number,number,number];
const GRIS_MED   = [200, 200, 200] as [number,number,number];
const BLANCO     = [255, 255, 255] as [number,number,number];
const NEGRO      = [30,  30,  30]  as [number,number,number];
const AZUL       = [56,  132, 186] as [number,number,number];
const AZUL_CLR   = [219, 234, 245] as [number,number,number];
const AMBAR      = [210, 141, 22]  as [number,number,number];
const AMBAR_CLR  = [253, 243, 215] as [number,number,number];

function header(doc: jsPDF, page: number) {
  doc.setFillColor(...VERDE);
  doc.rect(0, 0, 595, 28, 'F');
  doc.setFont('helvetica','bold'); doc.setFontSize(11); doc.setTextColor(...BLANCO);
  doc.text('ESTUDIO DEFINITIVO DE PRESA EN EL RÍO POROTOG', 297, 11, {align:'center'});
  doc.setFont('helvetica','normal'); doc.setFontSize(7.5);
  doc.text('Padrón de Usuarios · Sistema de Riego Comunitario Guanguilqui Porotog · Provincia Pichincha – Cantón Cayambe', 297, 21, {align:'center'});
  doc.setTextColor(...NEGRO);
  doc.setDrawColor(...VERDE_MED); doc.setLineWidth(1); doc.line(36,31,559,31);
  doc.setFont('helvetica','normal'); doc.setFontSize(7); doc.setTextColor(140,140,140);
  doc.text(`Página ${page}`, 559, 830, {align:'right'});
  doc.setTextColor(...NEGRO);
}

function footer(doc: jsPDF, investigador: string, fecha: string) {
  const y = 815;
  doc.setDrawColor(...GRIS_MED); doc.setLineWidth(0.5); doc.line(36, y, 559, y);
  doc.setFont('helvetica','normal'); doc.setFontSize(7); doc.setTextColor(140,140,140);
  doc.text(`Investigado por: ${investigador}`, 36, y+8);
  doc.text(`Fecha: ${fecha}`, 297, y+8, {align:'center'});
  doc.text('CONSORCIO CAYAMBE SPT', 559, y+8, {align:'right'});
  doc.setTextColor(...NEGRO);
}

function seccion(doc: jsPDF, y: number, titulo: string, color: [number,number,number]): number {
  doc.setFillColor(...color);
  doc.roundedRect(36, y, 523, 18, 3, 3, 'F');
  doc.setFont('helvetica','bold'); doc.setFontSize(9); doc.setTextColor(...BLANCO);
  doc.text(titulo.toUpperCase(), 297, y+12, {align:'center'});
  doc.setTextColor(...NEGRO);
  return y + 22;
}

const ESTILO_TABLA = {
  theme: 'plain' as const,
  margin: {left:36, right:36},
  tableWidth: 523,
  styles: {fontSize:8, cellPadding:{top:4,bottom:4,left:5,right:5}, textColor:NEGRO, lineColor:GRIS_MED, lineWidth:0.4},
  alternateRowStyles: {fillColor: GRIS_CLR},
};

const COL_LABEL = {fontStyle:'bold' as const, textColor:[80,80,80] as [number,number,number], cellWidth:90};

// ─── PDF DE LLENADO ───────────────────────────────────────────────────────
export const generatePadronPDF = (data: Record<string, any>) => {
  const doc = new jsPDF({unit:'pt', format:'a4', orientation:'portrait'});
  const d = data;
  const inv = d.investigadoPor || 'Técnico CONSORCIO CAYAMBE SPT';
  const fecha = d.fecha || new Date().toISOString().split('T')[0];
  const unidad = d.unidadArea === 'm2' ? 'm²' : 'Ha';

  // ══ PÁGINA 1: secciones 1, 2, 3 ══
  header(doc, 1);
  let y = 40;

  // S1 Propietario
  y = seccion(doc, y, '1. Datos del Propietario', VERDE);
  autoTable(doc, {...ESTILO_TABLA, startY:y,
    columnStyles:{0:{...COL_LABEL,fillColor:VERDE_CLR},2:{...COL_LABEL,fillColor:VERDE_CLR}},
    body:[
      ['Clave Catastral', d.claveCatastral||'—', 'Cédula', d.cedula||'—'],
      ['Apellidos', d.apellidos||'—', 'Nombres', d.nombres||'—'],
      ['Parroquia', d.parroquia||'—', 'Comunidad', d.comunidad||'—'],
      ['Sector', d.sector||'—', 'Tenencia', d.tenencia||'—'],
      ['Telf. Celular', d.telefonoCelular||'—', 'Telf. Casa', d.telefonoCasa||'—'],
      ['Hijos Hombres', String(d.hijosHombres??0), 'Hijos Mujeres', String(d.hijosMujeres??0)],
      ['Instrucción', d.instruccion||'—', '', ''],
    ]});
  y = (doc as any).lastAutoTable.finalY + 8;

  // S2 Predio y Riego
  y = seccion(doc, y, '2. Datos del Predio (UPA) y Riego', VERDE);
  const metodos = [
    d.metodoInundacion ? `Gravedad ${d.metodoInundacion}%` : '',
    d.metodoAspersion  ? `Aspers. ${d.metodoAspersion}%` : '',
    d.metodoGoteo      ? `Goteo ${d.metodoGoteo}%`       : '',
  ].filter(Boolean).join(' · ') || '—';
  autoTable(doc, {...ESTILO_TABLA, startY:y,
    columnStyles:{0:{...COL_LABEL,fillColor:VERDE_CLR},2:{...COL_LABEL,fillColor:VERDE_CLR}},
    body:[
      ['Organización Riego', d.organizacionRiego||'—', 'Código Predio', d.codigoPredio||'—'],
      ['Sector Comunidad', d.sectorComunidad||'—', 'N° Predio', d.numPredio||'—'],
      ['Canal', d.canal||'—', `Caudal (l/s)`, `${d.caudal||'—'}${d.tipoCaudal ? ' (' + d.tipoCaudal + ')' : ''}`],
      [`Área Total (${unidad})`, String(d.areaTotal??0), `Área Riego (${unidad})`, String(d.areaRiego??0)],
      [`Área sin Riego (${unidad})`, String(d.areaSinRiego??0), 'Frecuencia', d.frecuenciaRiego||'—'],
      ['Método Riego', metodos, 'Días / Horas Turno', `${d.diasRiego??0} días / ${d.horasTurno??0} h`],
      ['Tarifa', `$ ${d.valorTarifa??0} (${d.tipoTarifa||'—'})`, '¿Tiene reservorio?', d.tieneReservorio||'—'],
    ]});
  y = (doc as any).lastAutoTable.finalY + 8;

  // S3 Servicios
  y = seccion(doc, y, '3. Servicios Básicos y Ubicación Geográfica', AZUL);
  autoTable(doc, {...ESTILO_TABLA, startY:y,
    columnStyles:{0:{...COL_LABEL,fillColor:AZUL_CLR},2:{...COL_LABEL,fillColor:AZUL_CLR}},
    body:[
      ['Agua de Consumo', d.aguaConsumo?'SÍ':'NO', 'Energía Eléctrica', d.energiaElectrica?'SÍ':'NO'],
      ['Material Viv.', d.materialVivienda||'—', 'COTA (msnm)', d.cota||'—'],
      ['Coordenada X', d.coordX||'—', 'Coordenada Y', d.coordY||'—'],
    ]});

  footer(doc, inv, fecha);

  // ══ PÁGINA 2: secciones 4, 5, 6 ══
  doc.addPage();
  header(doc, 2);
  y = 40;

  // S4 Producción
  y = seccion(doc, y, '4. Datos del Sistema de Producción', AMBAR);
  const mapDestinos = (item: any) => {
    return [item.destAuto?'Auto':'', item.destMercado?'Merc':'', item.destAgro?'Agro':'', item.destExp?'Exp':''].filter(Boolean).join(', ');
  };

  const cultivosBody = d.cultivos?.length > 0
    ? d.cultivos.map((c:any) => [c.nombre||'—', `${c.superficie||0}`, c.esPrincipal?'SÍ':'', mapDestinos(c)])
    : [['—','—','—','—']];
  const animalesBody = d.animales?.length > 0
    ? d.animales.map((a:any) => [a.tipo||'—', String(a.cantidad??'—'), mapDestinos(a)])
    : [['—','—','—']];

  const yProd = y;
  autoTable(doc, {...ESTILO_TABLA, startY:yProd,
    margin:{left:36, right:265}, tableWidth:294,
    head:[['Cultivo','Sup.(m²)','Ppal.','Destino']], headStyles:{fillColor:AMBAR_CLR,textColor:NEGRO,fontStyle:'bold',fontSize:6.5},
    columnStyles:{0:{cellWidth:84}, 1:{cellWidth:50}, 2:{cellWidth:30}, 3:{cellWidth:130}},
    styles:{fontSize:6.5, cellPadding:3, lineColor:GRIS_MED, lineWidth:0.4},
    body: cultivosBody});
  const yAfterCultivos = (doc as any).lastAutoTable.finalY;

  autoTable(doc, {...ESTILO_TABLA, startY:yProd,
    margin:{left:340, right:36}, tableWidth:219,
    head:[['Animal / Especie','Cant.','Destino']], headStyles:{fillColor:AMBAR_CLR,textColor:NEGRO,fontStyle:'bold',fontSize:6.5},
    columnStyles:{0:{cellWidth:79}, 1:{cellWidth:30}, 2:{cellWidth:110}},
    styles:{fontSize:6.5, cellPadding:3, lineColor:GRIS_MED, lineWidth:0.4},
    body: animalesBody});

  y = Math.max(yAfterCultivos, (doc as any).lastAutoTable.finalY) + 6;
  autoTable(doc, {...ESTILO_TABLA, startY:y,
    columnStyles:{0:{...COL_LABEL,fillColor:AMBAR_CLR},2:{...COL_LABEL,fillColor:AMBAR_CLR}},
    body:[
      ['Uso Agua: Soberanía Alim.', `${d.usoSoberania??0}%`, 'Actividades Productivas', `${d.usoProductivas??0}%`],
    ]});
  y = (doc as any).lastAutoTable.finalY + 8;

  // S5 Encuesta Junta
  y = seccion(doc, y, '5. Datos de la Comunidad y Conocimiento de la Junta de Agua', VERDE);
  const sv = (v:string) => v==='si'?'SÍ': v==='no'?'NO':'N/S';
  autoTable(doc, {...ESTILO_TABLA, startY:y,
    columnStyles:{0:{...COL_LABEL,fillColor:VERDE_CLR},2:{...COL_LABEL,fillColor:VERDE_CLR}},
    body:[
      ['¿Tiene estatutos?', sv(d.tieneEstatutos), '¿Tiene reglamentos?', sv(d.tieneReglamentos)],
      ['¿Conoce la presa?', sv(d.conocePresa), '', ''],
      [{content:'DATOS DE LA COMUNIDAD', colSpan: 4, styles:{fillColor:VERDE_CLR, textColor:VERDE, halign:'center', fontStyle:'bold'}}],
      ['¿Cómo se elige a la directiva?', d.comoSeElige||'—', '¿Cómo se llama el Presidente de la Junta de Agua?', d.nombrePresidente||'—'],
      ['¿Conoce quién es el operador del sistema en su sector?', d.quienOpera||'—', '¿Cuántos años tiene este sistema de riego?', String(d.aniosSistema||'—')],
      ['¿Conoce cuántos Km tiene el canal principal?', String(d.kmCanal||'—'), 'Recibió capacitación', sv(d.recibioCapacitacion)],
      ['¿Le gustaría recibir capacitación?', sv(d.leGustariaCapacitacion), 'Temas capacitación', d.temasCapacitacion||'—'],
    ]});
  y = (doc as any).lastAutoTable.finalY + 8;

  // S6 Emplazamiento
  y = seccion(doc, y, '6. Emplazamiento – Croquis del Predio', GRIS_MED as [number,number,number]);
  doc.setDrawColor(...GRIS_MED); doc.setLineWidth(0.5);
  doc.setFillColor(252, 252, 252);
  const espacioH = Math.max(160, 810 - y - 30);
  doc.roundedRect(36, y, 523, espacioH, 3, 3, 'FD');


  footer(doc, inv, fecha);

  doc.save(`Padron_${d.cedula||d.apellidos||'SinCedula'}.pdf`);
};
