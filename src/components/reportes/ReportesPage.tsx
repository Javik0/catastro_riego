import { useState, useMemo } from 'react';
import {
  FileDown, FileSpreadsheet, FileText, Calendar,
  Users, MapPin, Filter, Loader2, BarChart3, Download,
  CheckCircle2, Clock, Layers, Building2,
} from 'lucide-react';
import { type FichaPredio, safeToDate } from '../../lib/types';
import { getNombreTecnico, PARROQUIAS, SECTORES, TECNICOS, PROJECT_TITLE, PROJECT_SUBTITLE, PROJECT_LOCATION } from '../../lib/constants';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';

interface Props {
  fichas: FichaPredio[];
  cultivosData: { tipo_cultivo: string; ficha_id: string; superficie_m2?: number; es_principal?: boolean }[];
  animalesData: { especie: string; ficha_id: string; cantidad: number }[];
  loading: boolean;
}
type ReportType = 'general' | 'sector' | 'parroquia' | 'comunidad' | 'tecnico' | 'fecha';

export default function ReportesPage({ fichas, cultivosData, animalesData }: Props) {
  const [reportType, setReportType] = useState<ReportType>('general');
  const [filterSector, setFilterSector] = useState('');
  const [filterParroquia, setFilterParroquia] = useState('');
  const [filterComunidad, setFilterComunidad] = useState('');
  const [filterTecnico, setFilterTecnico] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [generating, setGenerating] = useState<'pdf' | 'excel' | null>(null);
  const [lastGenerated, setLastGenerated] = useState<string | null>(null);

  // Lista dinámica de comunidades obtenida de las fichas reales
  const comunidadesList = useMemo(() => {
    const set = new Set<string>();
    fichas.forEach((f) => {
      const c = (f.sector_comunidad || '').trim();
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
        if (filterComunidad) result = result.filter((f) => (f.sector_comunidad || '').trim() === filterComunidad);
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
      };
      doc.setFontSize(8); doc.setFont('helvetica', 'bold');
      doc.text(subtitles[reportType], pageWidth / 2, 26, { align: 'center' });
      doc.setFont('helvetica', 'normal');
      doc.text(`Total de registros: ${data.length} | Generado: ${new Date().toLocaleDateString('es-EC')}`, pageWidth / 2, 30, { align: 'center' });

      const headers = ['#', 'Código', 'Propietario', 'Cédula', 'Parroquia', 'Sector', 'Comunidad', 'Área Total', 'Método Riego', 'Caudal', 'Técnico', 'Fecha'];
      const rows = data.map((f, i) => [
        i + 1, f.codigo_final,
        f.propietario || `${f.apellidos} ${f.nombres}`,
        f.cedula || '', f.parroquia, f.sector,
        (f.sector_comunidad || '').trim(),
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
        head: [headers], body: rows, startY: 33,
        styles: { fontSize: 6, cellPadding: 1.5 },
        headStyles: { fillColor: [30, 41, 59], textColor: 255, fontStyle: 'bold', fontSize: 6 },
        alternateRowStyles: { fillColor: [241, 245, 249] },
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
      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(fichasRows), 'Fichas');

      const fichaIds = new Set(data.map((f) => f.id));
      const cultivosF = cultivosData.filter((c) => fichaIds.has(c.ficha_id));
      if (cultivosF.length > 0) XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(cultivosF), 'Cultivos');

      const animalesF = animalesData.filter((a) => fichaIds.has(a.ficha_id));
      if (animalesF.length > 0) XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(animalesF), 'Animales');

      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet([
        { Métrica: 'Total Fichas', Valor: data.length },
        { Métrica: 'Área Total (m²)', Valor: data.reduce((s, f) => s + (f.area_total || 0), 0) },
        { Métrica: 'Cultivos Registrados', Valor: cultivosF.length },
        { Métrica: 'Animales Registrados', Valor: animalesF.length },
      ]), 'Resumen');

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
    { id: 'parroquia' as const, label: 'Por Parroquia', icon: MapPin, desc: 'Filtrar por parroquia', color: '#10b981' },
    { id: 'comunidad' as const, label: 'Por Comunidad', icon: Building2, desc: `${comunidadesList.length} comunidades`, color: '#ec4899' },
    { id: 'tecnico' as const, label: 'Por Técnico', icon: Users, desc: 'Producción por investigador', color: '#f59e0b' },
    { id: 'fecha' as const, label: 'Por Fecha', icon: Calendar, desc: 'Rango de fechas personalizado', color: '#8b5cf6' },
  ];

  const activeType = reportTypes.find((r) => r.id === reportType)!;

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
