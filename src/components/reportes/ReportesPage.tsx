import { useState } from 'react';
import {
  FileDown, FileSpreadsheet, FileText, Calendar,
  Users, MapPin, Filter, Loader2,
} from 'lucide-react';
import { type FichaPredio, safeToDate } from '../../lib/types';
import { getNombreTecnico, PARROQUIAS, TECNICOS, PROJECT_TITLE, PROJECT_SUBTITLE, PROJECT_LOCATION } from '../../lib/constants';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';

interface Props {
  fichas: FichaPredio[];
  cultivosData: { tipo_cultivo: string; ficha_id: string; superficie_m2?: number; es_principal?: boolean }[];
  animalesData: { especie: string; ficha_id: string; cantidad: number }[];
  loading: boolean;
}
type ReportType = 'general' | 'parroquia' | 'tecnico' | 'fecha';

export default function ReportesPage({ fichas, cultivosData, animalesData }: Props) {
  const [reportType, setReportType] = useState<ReportType>('general');
  const [filterParroquia, setFilterParroquia] = useState('');
  const [filterTecnico, setFilterTecnico] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [generating, setGenerating] = useState(false);

  const getFilteredFichas = (): FichaPredio[] => {
    let result = [...fichas];

    switch (reportType) {
      case 'parroquia':
        if (filterParroquia) result = result.filter((f) => f.parroquia === filterParroquia);
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
    setGenerating(true);
    try {
      const data = getFilteredFichas();
      const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });

      // Header
      const pageWidth = doc.internal.pageSize.getWidth();

      // Logos
      try {
        const logoIzq = await loadImage('/logo-izq.png');
        doc.addImage(logoIzq, 'PNG', 10, 5, 25, 22);
      } catch {}
      try {
        const logoDer = await loadImage('/logo-der.png');
        doc.addImage(logoDer, 'PNG', pageWidth - 35, 5, 25, 22);
      } catch {}

      // Title
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.text(PROJECT_TITLE, pageWidth / 2, 12, { align: 'center' });
      doc.setFontSize(8);
      doc.text(PROJECT_SUBTITLE, pageWidth / 2, 17, { align: 'center' });
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.text(PROJECT_LOCATION, pageWidth / 2, 21, { align: 'center' });

      // Subtitle
      const subtitles: Record<ReportType, string> = {
        general: 'REPORTE GENERAL DE FICHAS INVESTIGADAS',
        parroquia: `REPORTE POR PARROQUIA: ${filterParroquia || 'TODAS'}`,
        tecnico: `REPORTE POR TÉCNICO: ${filterTecnico ? getNombreTecnico(filterTecnico) : 'TODOS'}`,
        fecha: `REPORTE POR FECHA: ${fechaDesde || '...'} al ${fechaHasta || '...'}`,
      };

      doc.setFontSize(8);
      doc.setFont('helvetica', 'bold');
      doc.text(subtitles[reportType], pageWidth / 2, 26, { align: 'center' });
      doc.setFont('helvetica', 'normal');
      doc.text(`Total de registros: ${data.length} | Generado: ${new Date().toLocaleDateString('es-EC')}`, pageWidth / 2, 30, { align: 'center' });

      // Table
      const headers = ['#', 'Código', 'Propietario', 'Cédula', 'Parroquia', 'Sector', 'Área Total', 'Método Riego', 'Caudal', 'Técnico', 'Fecha'];
      const rows = data.map((f, i) => [
        i + 1,
        f.codigo_final,
        f.propietario || `${f.apellidos} ${f.nombres}`,
        f.cedula || '',
        f.parroquia,
        f.sector,
        f.area_total?.toLocaleString('es-EC') || '',
        [
          f.metodo_aspersion_pct ? `Asp:${f.metodo_aspersion_pct}%` : '',
          f.metodo_gravedad_pct ? `Grav:${f.metodo_gravedad_pct}%` : '',
          f.metodo_goteo_pct ? `Got:${f.metodo_goteo_pct}%` : '',
        ].filter(Boolean).join(' '),
        f.caudal_valor ? `${f.caudal_valor} l/s` : '',
        getNombreTecnico(f.creado_por),
        safeToDate(f.fecha_creacion).toLocaleDateString('es-EC'),
      ]);

      autoTable(doc, {
        head: [headers],
        body: rows,
        startY: 33,
        styles: { fontSize: 6, cellPadding: 1.5 },
        headStyles: { fillColor: [30, 41, 59], textColor: 255, fontStyle: 'bold', fontSize: 6 },
        alternateRowStyles: { fillColor: [241, 245, 249] },
        margin: { left: 10, right: 10 },
        didDrawPage: (data) => {
          // Footer
          const pageCount = doc.getNumberOfPages();
          doc.setFontSize(6);
          doc.setTextColor(128);
          doc.text(
            `Página ${data.pageNumber} de ${pageCount} | Consorcio Cayambe SPT - Prefectura de Pichincha`,
            pageWidth / 2,
            doc.internal.pageSize.getHeight() - 5,
            { align: 'center' }
          );
        },
      });

      doc.save(`reporte_${reportType}_${new Date().toISOString().split('T')[0]}.pdf`);
    } catch (err) {
      console.error('Error generating PDF:', err);
    } finally {
      setGenerating(false);
    }
  };

  const generateExcel = () => {
    setGenerating(true);
    try {
      const data = getFilteredFichas();
      const wb = XLSX.utils.book_new();

      // Hoja 1: Fichas
      const fichasRows = data.map((f) => ({
        'Código': f.codigo_final,
        'Propietario': f.propietario || `${f.apellidos} ${f.nombres}`,
        'Cédula': f.cedula,
        'Parroquia': f.parroquia,
        'Sector': f.sector,
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
      }));
      const ws1 = XLSX.utils.json_to_sheet(fichasRows);
      XLSX.utils.book_append_sheet(wb, ws1, 'Fichas');

      // Hoja 2: Cultivos
      const fichaIds = new Set(data.map((f) => f.id));
      const cultivosFiltered = cultivosData.filter((c) => fichaIds.has(c.ficha_id));
      if (cultivosFiltered.length > 0) {
        const ws2 = XLSX.utils.json_to_sheet(cultivosFiltered);
        XLSX.utils.book_append_sheet(wb, ws2, 'Cultivos');
      }

      // Hoja 3: Animales
      const animalesFiltered = animalesData.filter((a) => fichaIds.has(a.ficha_id));
      if (animalesFiltered.length > 0) {
        const ws3 = XLSX.utils.json_to_sheet(animalesFiltered);
        XLSX.utils.book_append_sheet(wb, ws3, 'Animales');
      }

      // Hoja 4: Resumen
      const resumen = [
        { 'Métrica': 'Total Fichas', 'Valor': data.length },
        { 'Métrica': 'Área Total (m²)', 'Valor': data.reduce((s, f) => s + (f.area_total || 0), 0) },
        { 'Métrica': 'Cultivos Registrados', 'Valor': cultivosFiltered.length },
        { 'Métrica': 'Animales Registrados', 'Valor': animalesFiltered.length },
      ];
      const ws4 = XLSX.utils.json_to_sheet(resumen);
      XLSX.utils.book_append_sheet(wb, ws4, 'Resumen');

      XLSX.writeFile(wb, `reporte_${reportType}_${new Date().toISOString().split('T')[0]}.xlsx`);
    } catch (err) {
      console.error('Error generating Excel:', err);
    } finally {
      setGenerating(false);
    }
  };

  const filteredCount = getFilteredFichas().length;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Generador de Reportes</h2>
        <p className="text-sm text-slate-400">Exporta datos del padrón de usuarios en PDF o Excel con encabezado institucional</p>
      </div>

      {/* Tipo de reporte */}
      <div className="bg-slate-800/40 rounded-xl border border-slate-700/30 p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Filter className="w-4 h-4 text-blue-400" />
          Tipo de Reporte
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {([
            { id: 'general', label: 'General', icon: FileText, desc: 'Todas las fichas' },
            { id: 'parroquia', label: 'Por Parroquia', icon: MapPin, desc: 'Filtrado por parroquia' },
            { id: 'tecnico', label: 'Por Técnico', icon: Users, desc: 'Producción por investigador' },
            { id: 'fecha', label: 'Por Fecha', icon: Calendar, desc: 'Rango personalizado' },
          ] as const).map(({ id, label, icon: Icon, desc }) => (
            <button
              key={id}
              onClick={() => setReportType(id)}
              className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                reportType === id
                  ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                  : 'bg-slate-800/30 border-slate-700/30 text-slate-400 hover:border-slate-600'
              }`}
            >
              <Icon className="w-5 h-5 mb-1" />
              <p className="text-xs font-medium">{label}</p>
              <p className="text-[10px] opacity-60">{desc}</p>
            </button>
          ))}
        </div>

        {/* Filtros específicos */}
        <div className="flex flex-wrap gap-3 pt-2">
          {reportType === 'parroquia' && (
            <select
              value={filterParroquia}
              onChange={(e) => setFilterParroquia(e.target.value)}
              className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/40 text-sm text-white cursor-pointer"
            >
              <option value="">Todas las parroquias</option>
              {PARROQUIAS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          )}
          {reportType === 'tecnico' && (
            <select
              value={filterTecnico}
              onChange={(e) => setFilterTecnico(e.target.value)}
              className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/40 text-sm text-white cursor-pointer"
            >
              <option value="">Todos los técnicos</option>
              {Object.entries(TECNICOS).map(([key, { nombre }]) => (
                <option key={key} value={key}>{nombre}</option>
              ))}
            </select>
          )}
          {reportType === 'fecha' && (
            <>
              <input type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/40 text-sm text-white cursor-pointer" />
              <input type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/40 text-sm text-white cursor-pointer" />
            </>
          )}
        </div>

        <div className="text-xs text-slate-400 pt-1">
          📋 {filteredCount} fichas seleccionadas para el reporte
        </div>
      </div>

      {/* Botones de descarga */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <button
          onClick={generatePDF}
          disabled={generating || filteredCount === 0}
          className="flex items-center justify-center gap-3 py-4 rounded-xl font-medium text-sm text-white transition-all disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          style={{
            background: generating ? '#475569' : 'linear-gradient(135deg, #ef4444, #dc2626)',
            boxShadow: '0 4px 14px rgba(239, 68, 68, 0.2)',
          }}
        >
          {generating ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileDown className="w-5 h-5" />}
          Descargar PDF
          <span className="text-xs opacity-70">(con logos)</span>
        </button>

        <button
          onClick={generateExcel}
          disabled={generating || filteredCount === 0}
          className="flex items-center justify-center gap-3 py-4 rounded-xl font-medium text-sm text-white transition-all disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          style={{
            background: generating ? '#475569' : 'linear-gradient(135deg, #22c55e, #16a34a)',
            boxShadow: '0 4px 14px rgba(34, 197, 94, 0.2)',
          }}
        >
          {generating ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileSpreadsheet className="w-5 h-5" />}
          Descargar Excel
          <span className="text-xs opacity-70">(4 hojas)</span>
        </button>
      </div>
    </div>
  );
}

// ── Utilidad: cargar imagen como base64 ──
function loadImage(src: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      canvas.getContext('2d')?.drawImage(img, 0, 0);
      resolve(canvas.toDataURL('image/png'));
    };
    img.onerror = reject;
    img.src = src;
  });
}
