import { useState, useMemo, useEffect } from 'react';
import {
  FileDown, FileSpreadsheet, FileText, Calendar,
  Users, MapPin, Filter, Loader2, BarChart3, Download,
  CheckCircle2, Clock, Layers, Building2,
} from 'lucide-react';
import { type FichaPredio, type PredioAdicional, safeToDate } from '../../lib/types';
import { getNombreTecnico, PARROQUIAS, SECTORES, TECNICOS, PROJECT_TITLE, PROJECT_SUBTITLE, PROJECT_LOCATION } from '../../lib/constants';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';

interface Props {
  fichas: FichaPredio[];
  cultivosData: { tipo_cultivo: string; ficha_id: string; superficie_m2?: number; es_principal?: boolean }[];
  animalesData: { especie: string; ficha_id: string; cantidad: number }[];
  prediosAdicionalesData: PredioAdicional[];
  loading: boolean;
}
type ReportType = 'general' | 'sector' | 'parroquia' | 'comunidad' | 'tecnico' | 'fecha' | 'auditoria';

export default function ReportesPage({ fichas, cultivosData, animalesData, prediosAdicionalesData }: Props) {
  const [reportType, setReportType] = useState<ReportType>('general');
  const [filterSector, setFilterSector] = useState('');
  const [filterParroquia, setFilterParroquia] = useState('');
  const [filterComunidad, setFilterComunidad] = useState('');
  const [filterTecnico, setFilterTecnico] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [generating, setGenerating] = useState<'pdf' | 'excel' | null>(null);
  const [lastGenerated, setLastGenerated] = useState<string | null>(null);

  // Estados para reporte de auditoría
  const [auditoria, setAuditoria] = useState<any>(null);
  const [loadingAuditoria, setLoadingAuditoria] = useState(false);
  const [busquedaAuditoria, setBusquedaAuditoria] = useState('');
  const [expandedRegante, setExpandedRegante] = useState<string | null>(null);

  useEffect(() => {
    if (!auditoria && !loadingAuditoria) {
      setLoadingAuditoria(true);
      fetch('/geo/auditoria.json')
        .then((res) => res.json())
        .then((data) => {
          setAuditoria(data);
          setLoadingAuditoria(false);
        })
        .catch((err) => {
          console.error('Error al cargar auditoria.json:', err);
          setLoadingAuditoria(false);
        });
    }
  }, []);

  // Lista dinámica de comunidades obtenida de las fichas reales
  const comunidadesList = useMemo(() => {
    const set = new Set<string>();
    fichas.forEach((f) => {
      const c = (f.comunidad || '').trim();
      if (c) set.add(c);
    });
    return Array.from(set).sort();
  }, [fichas]);

  const getFilteredFichas = (): FichaPredio[] => {
    let result = [...fichas];
    switch (reportType) {
      case 'sector':
        if (filterSector) result = result.filter((f) => f.sector === filterSector);
        break;
      case 'parroquia':
        if (filterParroquia) result = result.filter((f) => f.parroquia === filterParroquia);
        break;
      case 'comunidad':
        if (filterComunidad) result = result.filter((f) => (f.comunidad || '').trim() === filterComunidad);
        break;
      case 'tecnico':
        if (filterTecnico) result = result.filter((f) => f.creado_por === filterTecnico);
        break;
      case 'fecha':
        if (fechaDesde) result = result.filter((f) => safeToDate(f.fecha_creacion) >= new Date(fechaDesde));
        if (fechaHasta) {
          const hasta = new Date(fechaHasta);
          hasta.setHours(23, 59, 59);
          result = result.filter((f) => safeToDate(f.fecha_creacion) <= hasta);
        }
        break;
    }
    return result;
  };

  const generatePDF = async () => {
    setGenerating('pdf');
    try {
      const data = getFilteredFichas();
      const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      const pageWidth = doc.internal.pageSize.getWidth();

      // Logos — proporción real
      try {
        const logoIzq = await loadImageWithSize('/logo-izq.png');
        const hIzq = 14;
        const wIzq = (logoIzq.width / logoIzq.height) * hIzq;
        doc.addImage(logoIzq.data, 'PNG', 8, 6, wIzq, hIzq);
      } catch {}
      try {
        const logoDer = await loadImageWithSize('/logo-der.png');
        const hDer = 12;
        const wDer = (logoDer.width / logoDer.height) * hDer;
        doc.addImage(logoDer.data, 'PNG', pageWidth - wDer - 8, 7, wDer, hDer);
      } catch {}

      doc.setFontSize(10); doc.setFont('helvetica', 'bold');
      doc.text(PROJECT_TITLE, pageWidth / 2, 12, { align: 'center' });
      doc.setFontSize(8);
      doc.text(PROJECT_SUBTITLE, pageWidth / 2, 17, { align: 'center' });
      doc.setFont('helvetica', 'normal'); doc.setFontSize(7);
      doc.text(PROJECT_LOCATION, pageWidth / 2, 21, { align: 'center' });

      const subtitles: Record<ReportType, string> = {
        general: 'REPORTE GENERAL DE FICHAS INVESTIGADAS',
        sector: `REPORTE POR SECTOR: ${filterSector || 'TODOS'}`,
        parroquia: `REPORTE POR PARROQUIA: ${filterParroquia || 'TODAS'}`,
        comunidad: `REPORTE POR COMUNIDAD: ${filterComunidad || 'TODAS'}`,
        tecnico: `REPORTE POR TÉCNICO: ${filterTecnico ? getNombreTecnico(filterTecnico) : 'TODOS'}`,
        fecha: `REPORTE POR FECHA: ${fechaDesde || '...'} al ${fechaHasta || '...'}`,
        auditoria: 'REPORTE DE AUDITORÍA Y CONTROL DE CALIDAD',
      };
      doc.setFontSize(8); doc.setFont('helvetica', 'bold');
      doc.text(subtitles[reportType], pageWidth / 2, 26, { align: 'center' });
      doc.setFont('helvetica', 'normal');
      doc.text(`Total de registros: ${data.length} | Generado: ${new Date().toLocaleDateString('es-EC')}`, pageWidth / 2, 30, { align: 'center' });

      if (reportType === 'general' && auditoria) {
        // Título del bloque de auditoría sin emojis para evitar problemas de caracteres
        doc.setFontSize(8); doc.setFont('helvetica', 'bold'); doc.setTextColor(15, 23, 42); // Slate-900
        doc.text("CONSOLIDADO DE CALIDAD DE DATOS (AUDITORÍA DE DUPLICADOS Y OPTIMIZACIÓN)", 10, 35);
        doc.setTextColor(0, 0, 0); // Reset color
        
        const cardY = 38;
        const cardHeight = 17;
        const cardWidth = 43;
        const cardGap = 3.8;
        
        const cards = [
          {
            titleL1: 'Fichas en Campo',
            titleL2: '(Originales)',
            val: auditoria.resumen.totalFichasOriginales,
            valColor: [37, 99, 235], // Azul
            borderColor: [191, 219, 254],
            fillColor: [240, 246, 255]
          },
          {
            titleL1: 'Regantes Duplicados',
            titleL2: '(Detectados)',
            val: auditoria.resumen.totalRegantesUnicosDuplicados,
            valColor: [217, 119, 6], // Ámbar
            borderColor: [253, 230, 138],
            fillColor: [254, 251, 232]
          },
          {
            titleL1: 'Fichas Duplicadas',
            titleL2: '(Encontradas)',
            val: auditoria.resumen.totalFichasDuplicadas,
            valColor: [71, 85, 105], // Slate
            borderColor: [226, 232, 240],
            fillColor: [248, 250, 252]
          },
          {
            titleL1: 'Fichas Redundantes',
            titleL2: '(Reducidas)',
            val: auditoria.resumen.fichasRedundantesReducidas,
            valColor: [220, 38, 38], // Rojo
            borderColor: [254, 202, 202],
            fillColor: [254, 242, 242]
          },
          {
            titleL1: 'Fichas Finales',
            titleL2: '(Padrón Depurado)',
            val: auditoria.resumen.totalFichasUnificadas,
            valColor: [5, 150, 105], // Esmeralda
            borderColor: [167, 243, 208],
            fillColor: [236, 253, 245]
          },
          {
            titleL1: 'Reducción en BD',
            titleL2: '(Optimización)',
            val: `${auditoria.resumen.porcentajeReduccion}%`,
            valColor: [124, 58, 237], // Violeta
            borderColor: [233, 213, 255],
            fillColor: [245, 243, 255]
          }
        ];

        cards.forEach((c, idx) => {
          const cardX = 10 + idx * (cardWidth + cardGap);
          // Dibujar fondo de tarjeta
          doc.setFillColor(c.fillColor[0], c.fillColor[1], c.fillColor[2]);
          doc.setDrawColor(c.borderColor[0], c.borderColor[1], c.borderColor[2]);
          doc.setLineWidth(0.25);
          doc.roundedRect(cardX, cardY, cardWidth, cardHeight, 1.5, 1.5, 'FD');

          // Dibujar textos
          doc.setFontSize(6); 
          doc.setFont('helvetica', 'bold'); 
          doc.setTextColor(71, 85, 105); // Slate-600
          doc.text(c.titleL1, cardX + cardWidth / 2, cardY + 4.5, { align: 'center' });
          
          doc.setFontSize(5.5); 
          doc.setFont('helvetica', 'normal'); 
          doc.setTextColor(100, 116, 139); // Slate-500
          doc.text(c.titleL2, cardX + cardWidth / 2, cardY + 7.5, { align: 'center' });
          
          doc.setFontSize(10.5); 
          doc.setFont('helvetica', 'bold'); 
          doc.setTextColor(c.valColor[0], c.valColor[1], c.valColor[2]);
          doc.text(String(c.val), cardX + cardWidth / 2, cardY + 13.5, { align: 'center' });
        });
        
        doc.setTextColor(0, 0, 0); // Reset color
      }

      const tableStartY = (reportType === 'general' && auditoria)
        ? 64
        : 35;

      if (reportType === 'general' && auditoria) {
        doc.setFontSize(8); doc.setFont('helvetica', 'bold'); doc.setTextColor(15, 23, 42);
        doc.text("PADRÓN DE USUARIOS (DATOS UNIFICADOS Y DEPURADOS)", 10, tableStartY - 3);
        doc.setTextColor(0, 0, 0); // Reset color
      }

      const headers = ['#', 'Código del Lote', 'Propietario / Regante', 'Identificación\n(Cédula / Clave)', 'Ubicación\n(Parroquia / Sector / Comunidad)', 'Área Total', 'Área Riego', 'Técnico', 'Fecha'];
      
      const rows: any[] = [];
      data.forEach((f, i) => {
        // Ficha Principal
        rows.push([
          i + 1,
          f.codigo_final,
          f.propietario || `${f.apellidos} ${f.nombres}`,
          [
            f.cedula ? `C.I. ${f.cedula}` : '', 
            f.clave_catastral ? `ClvP ${f.clave_catastral}` : ''
          ].filter(Boolean).join('\n'),
          [
            f.parroquia || '', 
            f.sector || '', 
            (f.comunidad || '').trim()
          ].filter(Boolean).join('\n'),
          f.area_total ? `${f.area_total.toLocaleString('es-EC')} m²` : '0 m²',
          f.area_riego ? `${f.area_riego.toLocaleString('es-EC')} m²` : '0 m²',
          getNombreTecnico(f.creado_por),
          safeToDate(f.fecha_creacion).toLocaleDateString('es-EC'),
        ]);

        // Desglose de predios adicionales (tanto físicos como unificados virtuales)
        const adicionales = prediosAdicionalesData.filter((pa) => pa.ficha_id === f.id);
        adicionales.forEach((pa) => {
          // Buscamos si es una ficha virtual que tiene su respectivo registro original en las fichas para recuperar datos geográficos reales
          const fichaAdicionalFisica = fichas.find((x) => x.id === pa.id_adicional);
          
          const ubicacionAdicional = [
            fichaAdicionalFisica?.parroquia,
            fichaAdicionalFisica?.sector,
            fichaAdicionalFisica?.comunidad
          ].filter(Boolean).join(' / ');

          rows.push([
            { content: '', styles: { fillColor: [248, 250, 252], lineColor: [241, 245, 249] } }, // #
            { 
              content: '   - Predio Adicional', 
              colSpan: 2, 
              styles: { fontStyle: 'italic', textColor: [71, 85, 105], fillColor: [248, 250, 252], font: 'helvetica', fontSize: 5.5, lineColor: [241, 245, 249] } 
            }, // Código + Propietario
            { 
              content: pa.clave_catastral_otro ? `ClvP ${pa.clave_catastral_otro}` : '', 
              styles: { textColor: [71, 85, 105], fillColor: [248, 250, 252], fontSize: 5.5, lineColor: [241, 245, 249] } 
            }, // Identificación (Clave)
            { 
              content: ubicacionAdicional ? `Ubic: ${ubicacionAdicional}` : '', 
              styles: { textColor: [100, 116, 139], fillColor: [248, 250, 252], fontSize: 5, lineColor: [241, 245, 249] } 
            }, // Ubicación
            { 
              content: pa.area_total_otro ? `${pa.area_total_otro.toLocaleString('es-EC')} m²` : (pa.area_lote_asignado_otro ? `${pa.area_lote_asignado_otro.toLocaleString('es-EC')} m²` : '0 m²'), 
              styles: { textColor: [71, 85, 105], fillColor: [248, 250, 252], fontSize: 5.5, lineColor: [241, 245, 249] } 
            }, // Área Total
            { 
              content: pa.area_riego_otro ? `${pa.area_riego_otro.toLocaleString('es-EC')} m²` : '0 m²', 
              styles: { textColor: [71, 85, 105], fillColor: [248, 250, 252], fontSize: 5.5, lineColor: [241, 245, 249] } 
            }, // Área Riego
            { 
              content: '', 
              colSpan: 2, 
              styles: { fillColor: [248, 250, 252], lineColor: [241, 245, 249] } 
            } // Técnico + Fecha vacíos
          ]);
        });
      });

      autoTable(doc, {
        head: [headers], body: rows, startY: tableStartY,
        styles: { 
          fontSize: 6, 
          cellPadding: 1.5,
          valign: 'middle',
          lineColor: [226, 232, 240], // Bordes muy finos de color Slate-200
          lineWidth: 0.1,
        },
        headStyles: { 
          fillColor: [15, 23, 42], // Slate-900 muy moderno
          textColor: 255, 
          fontStyle: 'bold', 
          fontSize: 6,
          halign: 'left',
        },
        alternateRowStyles: { 
          fillColor: [255, 255, 255] 
        },
        margin: { left: 10, right: 10 },
        didDrawPage: (d) => {
          const pc = doc.getNumberOfPages();
          doc.setFontSize(6); doc.setTextColor(128);
          doc.text(
            `Página ${d.pageNumber} de ${pc} | Consorcio Cayambe SPT — Prefectura de Pichincha`,
            pageWidth / 2, doc.internal.pageSize.getHeight() - 5, { align: 'center' }
          );
        },
      });

      doc.save(`reporte_${reportType}_${new Date().toISOString().split('T')[0]}.pdf`);
      setLastGenerated(`PDF (${data.length} fichas)`);
    } catch (err) {
      console.error('Error generating PDF:', err);
    } finally {
      setGenerating(null);
    }
  };

  const generateExcel = () => {
    setGenerating('excel');
    try {
      const data = getFilteredFichas();
      const wb = XLSX.utils.book_new();

      const fichasRows: any[] = [];
      data.forEach((f) => {
        // Ficha Principal
        fichasRows.push({
          'Código': f.codigo_final,
          'Propietario': f.propietario || `${f.apellidos} ${f.nombres}`,
          'Cédula': f.cedula,
          'Parroquia': f.parroquia,
          'Sector': f.sector,
          'Comunidad': f.comunidad,
          'Sector Comunidad': f.sector_comunidad,
          'Clave Catastral': f.clave_catastral,
          'Área Total (m²)': f.area_total,
          'Área Riego (m²)': f.area_riego,
          'Área Sin Riego (m²)': f.area_sin_riego,
          'Caudal (l/s)': f.caudal_valor,
          'Tipo Caudal': f.caudal_tipo,
          'Frecuencia Riego': f.frecuencia_riego,
          'Gravedad (%)': f.metodo_gravedad_pct,
          'Aspersión (%)': f.metodo_aspersion_pct,
          'Goteo (%)': f.metodo_goteo_pct,
          'COTA (msnm)': f.cota_msnm,
          'X (UTM)': f.coord_x_utm,
          'Y (UTM)': f.coord_y_utm,
          'Técnico': getNombreTecnico(f.creado_por),
          'Fecha': safeToDate(f.fecha_creacion).toLocaleDateString('es-EC'),
          'Tenencia': f.tenencia_predio,
          'Material Construcción': f.material_construccion,
          'Observaciones': f.observaciones,
        });

        // Predios Adicionales
        const adicionales = prediosAdicionalesData.filter((pa) => pa.ficha_id === f.id);
        adicionales.forEach((pa) => {
          const fichaAdicionalFisica = fichas.find((x) => x.id === pa.id_adicional);

          fichasRows.push({
            'Código': '  ↳ Predio Adic.',
            'Propietario': '',
            'Cédula': '',
            'Parroquia': fichaAdicionalFisica?.parroquia || '',
            'Sector': fichaAdicionalFisica?.sector || '',
            'Comunidad': (fichaAdicionalFisica?.comunidad || '').trim(),
            'Sector Comunidad': '',
            'Clave Catastral': pa.clave_catastral_otro || '',
            'Área Total (m²)': pa.area_total_otro || pa.area_lote_asignado_otro || 0,
            'Área Riego (m²)': pa.area_riego_otro || 0,
            'Área Sin Riego (m²)': pa.area_sin_riego_otro || 0,
            'Caudal (l/s)': '',
            'Tipo Caudal': '',
            'Frecuencia Riego': '',
            'Gravedad (%)': '',
            'Aspersión (%)': '',
            'Goteo (%)': '',
            'COTA (msnm)': '',
            'X (UTM)': '',
            'Y (UTM)': '',
            'Técnico': '',
            'Fecha': '',
            'Tenencia': '',
            'Material Construcción': '',
            'Observaciones': pa.observaciones_otro || '',
          });
        });
      });
      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(fichasRows), 'Fichas');

      const fichaIds = new Set(data.map((f) => f.id));
      const cultivosF = cultivosData.filter((c) => fichaIds.has(c.ficha_id));
      if (cultivosF.length > 0) XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(cultivosF), 'Cultivos');

      const animalesF = animalesData.filter((a) => fichaIds.has(a.ficha_id));
      if (animalesF.length > 0) XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(animalesF), 'Animales');

      const resumenRows: { Métrica: string; Valor: string | number }[] = [
        { 'Métrica': 'Total Fichas (Unificadas en Padrón)', 'Valor': data.length },
        { 'Métrica': 'Área Total Investigada (m²)', 'Valor': data.reduce((s, f) => s + (f.area_total || 0), 0) },
        { 'Métrica': 'Cultivos Registrados', 'Valor': cultivosF.length },
        { 'Métrica': 'Animales Registrados', 'Valor': animalesF.length },
      ];

      if (auditoria) {
        resumenRows.push(
          { 'Métrica': 'Fichas Originales Registradas en Campo (QField)', 'Valor': auditoria.resumen.totalFichasOriginales },
          { 'Métrica': 'Regantes Únicos con Fichas Duplicadas', 'Valor': auditoria.resumen.totalRegantesUnicosDuplicados },
          { 'Métrica': 'Total de Fichas Involucradas en Duplicidad', 'Valor': auditoria.resumen.totalFichasDuplicadas },
          { 'Métrica': 'Fichas Redundantes que se Reducirán', 'Valor': auditoria.resumen.fichasRedundantesReducidas },
          { 'Métrica': 'Porcentaje de Optimización de Base de Datos', 'Valor': `${auditoria.resumen.porcentajeReduccion}%` }
        );
      }

      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(resumenRows), 'Resumen');

      XLSX.writeFile(wb, `reporte_${reportType}_${new Date().toISOString().split('T')[0]}.xlsx`);
      setLastGenerated(`Excel (${data.length} fichas, 4 hojas)`);
    } catch (err) {
      console.error('Error generating Excel:', err);
    } finally {
      setGenerating(null);
    }
  };

  const filteredCount = getFilteredFichas().length;
  const areaTotal = getFilteredFichas().reduce((s, f) => s + (f.area_total || 0), 0);

  const reportTypes = [
    { id: 'general' as const, label: 'General', icon: FileText, desc: 'Todas las fichas investigadas', color: '#3b82f6' },
    { id: 'sector' as const, label: 'Por Sector', icon: Layers, desc: 'Guanguilqui / Guang-Porotog', color: '#06b6d4' },
    { id: 'parroquia' as const, label: 'Por Parroquia', icon: MapPin, desc: 'Filtrar por parroquia', color: '#ec4899' },
    { id: 'comunidad' as const, label: 'Por Comunidad', icon: Building2, desc: `${comunidadesList.length} comunidades`, color: '#ec4899' },
    { id: 'tecnico' as const, label: 'Por Técnico', icon: Users, desc: 'Producción por investigador', color: '#f59e0b' },
    { id: 'fecha' as const, label: 'Por Fecha', icon: Calendar, desc: 'Rango de fechas personalizado', color: '#8b5cf6' },
    { id: 'auditoria' as const, label: 'Auditoría y Calidad', icon: CheckCircle2, desc: 'Control de duplicados y optimización', color: '#10b981' },
  ];

  const regantesFiltrados = useMemo(() => {
    if (!auditoria || !auditoria.regantesUnificados) return [];
    if (!busquedaAuditoria.trim()) return auditoria.regantesUnificados;
    const q = busquedaAuditoria.toLowerCase();
    return auditoria.regantesUnificados.filter((r: any) => 
      r.apellidos.toLowerCase().includes(q) ||
      r.nombres.toLowerCase().includes(q) ||
      (r.cedula || '').includes(q)
    );
  }, [auditoria, busquedaAuditoria]);

  const activeType = reportTypes.find((r) => r.id === reportType) || reportTypes[0];

  const selectStyle = {
    background: 'var(--bg-input)',
    border: '1px solid var(--border-input)',
    color: 'var(--text-primary)',
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <BarChart3 className="w-6 h-6 text-blue-400" />
          Generador de Reportes
        </h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Exporta datos del padrón de usuarios con encabezado institucional y logos oficiales
        </p>
      </div>

      {/* Report Type Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {reportTypes.map(({ id, label, icon: Icon, desc, color }) => (
          <button
            key={id}
            onClick={() => setReportType(id)}
            className={`relative p-4 rounded-xl border-2 text-left transition-all cursor-pointer group overflow-hidden ${
              reportType === id ? 'shadow-lg' : 'hover:shadow-md'
            }`}
            style={{
              background: reportType === id ? `${color}10` : 'var(--bg-card)',
              borderColor: reportType === id ? `${color}60` : 'var(--border-color)',
            }}
          >
            {/* Glow effect when selected */}
            {reportType === id && (
              <div className="absolute inset-0 opacity-5" style={{ background: `radial-gradient(circle at 30% 30%, ${color}, transparent 70%)` }} />
            )}
            <div className="relative">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 transition-transform group-hover:scale-110"
                style={{ background: `${color}20` }}
              >
                <Icon className="w-5 h-5" style={{ color }} />
              </div>
              <p className="text-sm font-semibold" style={{ color: reportType === id ? color : 'var(--text-primary)' }}>{label}</p>
              <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{desc}</p>
            </div>
          </button>
        ))}
      </div>

      {reportType !== 'auditoria' ? (
        <>
          {/* Filters + Stats */}
          <div
            className="rounded-xl border p-5"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
          >
            <div className="flex flex-wrap items-center gap-4">
              {/* Icon del tipo seleccionado */}
              <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: `${activeType.color}15` }}>
                <Filter className="w-4 h-4" style={{ color: activeType.color }} />
              </div>

              {/* Filtros dinámicos */}
              {reportType === 'sector' && (
                <select value={filterSector} onChange={(e) => setFilterSector(e.target.value)}
                  className="px-3 py-2 rounded-lg text-sm cursor-pointer min-w-[180px]" style={selectStyle}>
                  <option value="">Todos los sectores</option>
                  {SECTORES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              )}
              {reportType === 'parroquia' && (
                <select value={filterParroquia} onChange={(e) => setFilterParroquia(e.target.value)}
                  className="px-3 py-2 rounded-lg text-sm cursor-pointer min-w-[180px]" style={selectStyle}>
                  <option value="">Todas las parroquias</option>
                  {PARROQUIAS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              )}
              {reportType === 'comunidad' && (
                <select value={filterComunidad} onChange={(e) => setFilterComunidad(e.target.value)}
                  className="px-3 py-2 rounded-lg text-sm cursor-pointer min-w-[220px]" style={selectStyle}>
                  <option value="">Todas las comunidades ({comunidadesList.length})</option>
                  {comunidadesList.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              )}
              {reportType === 'tecnico' && (
                <select value={filterTecnico} onChange={(e) => setFilterTecnico(e.target.value)}
                  className="px-3 py-2 rounded-lg text-sm cursor-pointer min-w-[180px]" style={selectStyle}>
                  <option value="">Todos los técnicos</option>
                  {Object.entries(TECNICOS).map(([key, { nombre }]) => (
                    <option key={key} value={key}>{nombre}</option>
                  ))}
                </select>
              )}
              {reportType === 'fecha' && (
                <>
                  <div className="flex items-center gap-2">
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Desde:</span>
                    <input type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)}
                      className="px-3 py-2 rounded-lg text-sm cursor-pointer" style={selectStyle} />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Hasta:</span>
                    <input type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)}
                      className="px-3 py-2 rounded-lg text-sm cursor-pointer" style={selectStyle} />
                  </div>
                </>
              )}
              {reportType === 'general' && (
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Se exportarán todas las fichas investigadas sin filtros
                </span>
              )}

              {/* Stats */}
              <div className="ml-auto flex items-center gap-4">
                <div className="text-right">
                  <p className="text-2xl font-bold" style={{ color: activeType.color }}>{filteredCount}</p>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Fichas</p>
                </div>
                <div className="w-px h-10" style={{ background: 'var(--border-color)' }} />
                <div className="text-right">
                  <p className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {(areaTotal / 10000).toFixed(1)}
                  </p>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Hectáreas</p>
                </div>
              </div>
            </div>
          </div>

          {/* Download buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* PDF */}
            <button
              onClick={generatePDF}
              disabled={generating !== null || filteredCount === 0}
              className="group relative flex items-center gap-4 p-5 rounded-xl border-2 text-left transition-all disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed overflow-hidden"
              style={{
                background: 'var(--bg-card)',
                borderColor: generating === 'pdf' ? '#ef444480' : 'var(--border-color)',
              }}
            >
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ background: 'linear-gradient(135deg, rgba(239,68,68,0.04), transparent)' }} />
              <div className="relative w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: 'rgba(239,68,68,0.1)' }}>
                {generating === 'pdf' ? (
                  <Loader2 className="w-6 h-6 text-red-400 animate-spin" />
                ) : (
                  <FileDown className="w-6 h-6 text-red-400" />
                )}
              </div>
              <div className="relative flex-1 min-w-0">
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {generating === 'pdf' ? 'Generando PDF...' : 'Descargar PDF'}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Reporte con logos institucionales y encabezado oficial
                </p>
              </div>
              <Download className="w-5 h-5 shrink-0 opacity-30 group-hover:opacity-60 transition-opacity" style={{ color: 'var(--text-secondary)' }} />
            </button>

            {/* Excel */}
            <button
              onClick={generateExcel}
              disabled={generating !== null || filteredCount === 0}
              className="group relative flex items-center gap-4 p-5 rounded-xl border-2 text-left transition-all disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed overflow-hidden"
              style={{
                background: 'var(--bg-card)',
                borderColor: generating === 'excel' ? '#22c55e80' : 'var(--border-color)',
              }}
            >
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ background: 'linear-gradient(135deg, rgba(34,197,94,0.04), transparent)' }} />
              <div className="relative w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: 'rgba(34,197,94,0.1)' }}>
                {generating === 'excel' ? (
                  <Loader2 className="w-6 h-6 text-emerald-400 animate-spin" />
                ) : (
                  <FileSpreadsheet className="w-6 h-6 text-emerald-400" />
                )}
              </div>
              <div className="relative flex-1 min-w-0">
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {generating === 'excel' ? 'Generando Excel...' : 'Descargar Excel'}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  4 hojas: Fichas, Cultivos, Animales y Resumen estadístico
                </p>
              </div>
              <Download className="w-5 h-5 shrink-0 opacity-30 group-hover:opacity-60 transition-opacity" style={{ color: 'var(--text-secondary)' }} />
            </button>
          </div>

          {/* Last generated status */}
          {lastGenerated && (
            <div
              className="flex items-center gap-2 px-4 py-3 rounded-lg border"
              style={{ background: 'rgba(34,197,94,0.05)', borderColor: 'rgba(34,197,94,0.2)' }}
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span className="text-xs text-emerald-400">Último reporte generado: {lastGenerated}</span>
              <Clock className="w-3 h-3 text-emerald-400/50 ml-1" />
              <span className="text-[10px] text-emerald-400/50">{new Date().toLocaleTimeString('es-EC')}</span>
            </div>
          )}
        </>
      ) : (
        <div className="space-y-6">
          {loadingAuditoria ? (
            <div className="flex items-center justify-center p-12 rounded-xl border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Cargando datos de auditoría...</p>
              </div>
            </div>
          ) : auditoria ? (
            <>
              {/* Tarjetas de Métricas de Auditoría */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <p className="text-2xl font-bold text-blue-400">{auditoria.resumen.totalFichasOriginales}</p>
                  <p className="text-[10px] uppercase font-semibold tracking-wider mt-1" style={{ color: 'var(--text-muted)' }}>Fichas Originales</p>
                </div>
                <div className="p-4 rounded-xl border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <p className="text-2xl font-bold text-amber-400">{auditoria.resumen.totalRegantesUnicosDuplicados}</p>
                  <p className="text-[10px] uppercase font-semibold tracking-wider mt-1" style={{ color: 'var(--text-muted)' }}>Regantes Duplicados</p>
                </div>
                <div className="p-4 rounded-xl border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <p className="text-2xl font-bold text-emerald-400">-{auditoria.resumen.fichasRedundantesReducidas}</p>
                  <p className="text-[10px] uppercase font-semibold tracking-wider mt-1" style={{ color: 'var(--text-muted)' }}>Fichas Reducidas</p>
                </div>
                <div className="p-4 rounded-xl border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <p className="text-2xl font-bold text-purple-400">{auditoria.resumen.porcentajeReduccion}%</p>
                  <p className="text-[10px] uppercase font-semibold tracking-wider mt-1" style={{ color: 'var(--text-muted)' }}>Optimización de Carga</p>
                </div>
              </div>

              {/* Caja de búsqueda de regantes */}
              <div className="p-4 rounded-xl border flex items-center gap-3" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                <Filter className="w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar regante unificado por cédula, nombre o apellido..."
                  value={busquedaAuditoria}
                  onChange={(e) => setBusquedaAuditoria(e.target.value)}
                  className="bg-transparent text-sm border-0 focus:ring-0 focus:outline-none w-full"
                  style={{ color: 'var(--text-primary)' }}
                />
              </div>

              {/* Listado de regantes unificados */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Lista de Regantes Unificados ({regantesFiltrados.length})
                </h3>
                {regantesFiltrados.length === 0 ? (
                  <p className="text-xs p-8 border rounded-xl text-center" style={{ color: 'var(--text-muted)', background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                    No se encontraron regantes que coincidan con la búsqueda.
                  </p>
                ) : (
                  <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                    {regantesFiltrados.map((r: any) => {
                      const isExpanded = expandedRegante === r.id;
                      const totalFichas = r.fichasSecundarias.length + 1;
                      return (
                        <div
                          key={r.id}
                          className="border rounded-xl transition-all"
                          style={{
                            background: 'var(--bg-card)',
                            borderColor: isExpanded ? 'rgba(16,185,129,0.4)' : 'var(--border-color)',
                          }}
                        >
                          {/* Cabecera del item */}
                          <button
                            onClick={() => setExpandedRegante(isExpanded ? null : r.id)}
                            className="w-full p-4 flex items-center justify-between text-left cursor-pointer focus:outline-none"
                          >
                            <div>
                              <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                                {r.apellidos} {r.nombres}
                              </p>
                              <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                                {r.cedula ? `Cédula: ${r.cedula}` : 'Unificado por coincidencia fonética de nombre'} | {r.fichaMadre.sectorComunidad || 'Sin sector'}
                              </p>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className="text-[11px] px-2.5 py-1 rounded-full font-medium" style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981' }}>
                                {totalFichas} fichas unificadas
                              </span>
                              <span className="text-xs transition-transform" style={{ color: 'var(--text-secondary)' }}>
                                {isExpanded ? '▲' : '▼'}
                              </span>
                            </div>
                          </button>

                          {/* Contenido desplegado */}
                          {isExpanded && (
                            <div className="p-4 pt-0 border-t" style={{ borderColor: 'var(--border-color)' }}>
                              <div className="space-y-4 mt-4">
                                {/* Ficha Madre */}
                                <div className="p-3.5 rounded-lg border" style={{ background: 'var(--bg-primary)', borderColor: 'rgba(59,130,246,0.2)' }}>
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded" style={{ background: '#3b82f620', color: '#3b82f6' }}>Ficha Madre (Mayor Área)</span>
                                    <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>ID: {r.fichaMadre.id}</span>
                                  </div>
                                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                                    <div>
                                      <p style={{ color: 'var(--text-muted)' }}>Clave Catastral</p>
                                      <p className="font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>{r.fichaMadre.claveCatastral}</p>
                                    </div>
                                    <div>
                                      <p style={{ color: 'var(--text-muted)' }}>Área Total</p>
                                      <p className="font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>{r.fichaMadre.areaTotal.toLocaleString('es-EC')} m²</p>
                                    </div>
                                    <div>
                                      <p style={{ color: 'var(--text-muted)' }}>Técnico</p>
                                      <p className="font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>{r.fichaMadre.creadoPor}</p>
                                    </div>
                                    <div>
                                      <p style={{ color: 'var(--text-muted)' }}>Fecha</p>
                                      <p className="font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>{new Date(r.fichaMadre.fechaCreacion).toLocaleDateString('es-EC')}</p>
                                    </div>
                                  </div>
                                </div>

                                {/* Fichas Secundarias */}
                                <div className="space-y-2">
                                  <p className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Predios Secundarios Unificados (Agregados a la sección "Otros Predios"):</p>
                                  <div className="space-y-2">
                                    {r.fichasSecundarias.map((fs: any) => (
                                      <div key={fs.id} className="p-3 rounded-lg border text-[11px] grid grid-cols-1 md:grid-cols-5 gap-3 items-center" style={{ background: 'var(--bg-primary)', borderColor: 'var(--border-color)' }}>
                                        <div className="md:col-span-2">
                                          <p style={{ color: 'var(--text-muted)' }}>Predio Secundario (Clave)</p>
                                          <p className="font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>{fs.claveCatastral}</p>
                                          <p className="text-[9px] mt-0.5 overflow-hidden text-ellipsis whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>ID: {fs.id}</p>
                                        </div>
                                        <div>
                                          <p style={{ color: 'var(--text-muted)' }}>Área</p>
                                          <p className="font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>{fs.areaTotal.toLocaleString('es-EC')} m²</p>
                                        </div>
                                        <div>
                                          <p style={{ color: 'var(--text-muted)' }}>Técnico / Fecha</p>
                                          <p className="font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>{fs.creadoPor}</p>
                                          <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{new Date(fs.fechaCreacion).toLocaleDateString('es-EC')}</p>
                                        </div>
                                        <div className="text-right">
                                          <span className="inline-block text-[10px] px-2 py-0.5 rounded font-medium" style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}>
                                            {fs.cantCultivos} cult. / {fs.cantAnimales} anim. reasociados
                                          </span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <p className="text-xs p-4 border rounded-xl text-center" style={{ color: 'var(--text-muted)', background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
              No se pudo cargar la información de auditoría. Asegúrate de haber ejecutado el script de exportación.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Utilidad: cargar imagen con dimensiones reales ──
function loadImageWithSize(src: string): Promise<{ data: string; width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      canvas.getContext('2d')?.drawImage(img, 0, 0);
      resolve({ data: canvas.toDataURL('image/png'), width: img.naturalWidth, height: img.naturalHeight });
    };
    img.onerror = reject;
    img.src = src;
  });
}
