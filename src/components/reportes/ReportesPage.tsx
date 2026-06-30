import { useState, useMemo, useEffect } from 'react';
import { useFiltros } from '../../hooks/useFiltros';
import {
  FileDown, FileSpreadsheet, FileText, Calendar,
  Users, MapPin, Filter, Loader2, BarChart3, Download,
  CheckCircle2, Clock, Layers, Building2,
} from 'lucide-react';
import { type FichaPredio, type PredioAdicional, safeToDate } from '../../lib/types';
import { getNombreTecnico, PARROQUIAS, TECNICOS, PROJECT_TITLE, PROJECT_SUBTITLE, PROJECT_LOCATION, COMUNIDADES, COMUNIDADES_POR_SECTOR, META_COMUNEROS } from '../../lib/constants';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

interface Props {
  fichas: FichaPredio[];
  allFichas: FichaPredio[];
  cultivosData: { tipo_cultivo: string; ficha_id: string; superficie_m2?: number; es_principal?: boolean }[];
  animalesData: { especie: string; ficha_id: string; cantidad: number }[];
  prediosAdicionalesData: PredioAdicional[];
  loading: boolean;
}
type ReportType = 'general' | 'sector' | 'parroquia' | 'comunidad' | 'tecnico' | 'fecha' | 'ejecutivo' | 'auditoria' | 'resumen_sectores';


export default function ReportesPage({ fichas, allFichas, cultivosData, animalesData, prediosAdicionalesData }: Props) {
  const { filtros } = useFiltros();
  const [reportType, setReportType] = useState<ReportType>('general');
  const [filterSector, setFilterSector] = useState('');
  const [filterParroquia, setFilterParroquia] = useState('');
  const [filterComunidad, setFilterComunidad] = useState('');

  useEffect(() => {
    if (filtros.sectorInv && filterComunidad) {
      const pertenecientes = COMUNIDADES_POR_SECTOR[filtros.sectorInv] || [];
      if (!pertenecientes.includes(filterComunidad)) {
        setFilterComunidad('');
      }
    }
  }, [filtros.sectorInv, filterComunidad]);
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

  const tecnicosUnicos = useMemo(() => {
    return Array.from(new Set(Object.values(TECNICOS).map((t) => t.nombre))).sort();
  }, []);

  const getFilteredFichas = (): FichaPredio[] => {
    let result = [...fichas];
    switch (reportType) {
      case 'sector':
        if (filterSector) result = result.filter((f) => f.sector_investigacion === filterSector);
        break;
      case 'parroquia':
        if (filterParroquia) result = result.filter((f) => f.parroquia === filterParroquia);
        break;
      case 'comunidad':
        if (filterComunidad) result = result.filter((f) => (f.comunidad || '').trim() === filterComunidad);
        break;
      case 'tecnico':
        if (filterTecnico) result = result.filter((f) => getNombreTecnico(f.creado_por) === filterTecnico);
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

  const buildPdfDoc = async (dataToRender: FichaPredio[], subtitleText: string, showAuditoria: boolean = false) => {
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

      doc.setFontSize(8); doc.setFont('helvetica', 'bold');
      doc.text(subtitleText, pageWidth / 2, 26, { align: 'center' });
      doc.setFont('helvetica', 'normal');
      doc.text(`Total de registros: ${dataToRender.length} | Generado: ${new Date().toLocaleDateString('es-EC')}`, pageWidth / 2, 30, { align: 'center' });

      if (showAuditoria && auditoria) {
        // Título del bloque de auditoría sin emojis para evitar problemas de caracteres
        doc.setFontSize(8); doc.setFont('helvetica', 'bold'); doc.setTextColor(15, 23, 42); // Slate-900
        doc.text("CONSOLIDADO DE CALIDAD DE DATOS (AUDITORÍA DE DUPLICADOS Y OPTIMIZACIÓN)", 10, 35);
        doc.setTextColor(0, 0, 0); // Reset color
        
        const cardY = 38;
        const cardHeight = 15;
        const cardWidth = 135.5;
        const cardGap = 6;
        
        // Tarjeta 1: Fichas Totales
        const card1X = 10;
        doc.setFillColor(255, 255, 255); // Fondo blanco sólido para mejor impresión
        doc.setDrawColor(30, 41, 59); // Borde Slate-800 oscuro sólido
        doc.setLineWidth(0.4);
        doc.roundedRect(card1X, cardY, cardWidth, cardHeight, 1.5, 1.5, 'FD');

        // Textos Tarjeta 1
        doc.setFontSize(7.5); doc.setFont('helvetica', 'bold'); doc.setTextColor(30, 41, 59);
        doc.text("FICHAS TOTALES INVESTIGADAS EN CAMPO", card1X + cardWidth / 2, cardY + 4.5, { align: 'center' });
        
        const totalOriginalesStr = Number(auditoria.resumen.totalFichasOriginales).toLocaleString('es-EC');
        doc.setFontSize(13); doc.setFont('helvetica', 'bold'); doc.setTextColor(29, 78, 216); // Azul sólido
        doc.text(totalOriginalesStr, card1X + cardWidth / 2, cardY + 9.5, { align: 'center' });
        
        doc.setFontSize(6.5); doc.setFont('helvetica', 'normal'); doc.setTextColor(71, 85, 105);
        doc.text("Total de registros levantados originalmente mediante QField Cloud", card1X + cardWidth / 2, cardY + 13, { align: 'center' });

        // Tarjeta 2: Total activas (equivalente al conteo de QField)
        const card2X = 10 + cardWidth + cardGap;
        doc.setFillColor(255, 255, 255);
        doc.setDrawColor(5, 150, 105); // Borde verde esmeralda
        doc.setLineWidth(0.4);
        doc.roundedRect(card2X, cardY, cardWidth, cardHeight, 1.5, 1.5, 'FD');

        // Textos Tarjeta 2
        doc.setFontSize(7.5); doc.setFont('helvetica', 'bold'); doc.setTextColor(30, 41, 59);
        doc.text("TOTAL FICHAS ACTIVAS EN CATASTRO (= QField)", card2X + cardWidth / 2, cardY + 4.5, { align: 'center' });
        
        const totalActivasStr = Number(auditoria.resumen.totalFichasUnificadas).toLocaleString('es-EC');
        doc.setFontSize(13); doc.setFont('helvetica', 'bold'); doc.setTextColor(5, 150, 105); // Verde esmeralda
        doc.text(totalActivasStr, card2X + cardWidth / 2, cardY + 9.5, { align: 'center' });
        
        doc.setFontSize(6.5); doc.setFont('helvetica', 'italic'); doc.setTextColor(71, 85, 105);
        doc.text("Base de datos alineada 1:1 con datos locales de QFieldCloud", card2X + cardWidth / 2, cardY + 13, { align: 'center' });
        
        doc.setTextColor(0, 0, 0); // Reset color
      }

      const tableStartY = (showAuditoria && auditoria)
        ? 62
        : 35;

      if (showAuditoria && auditoria) {
        doc.setFontSize(8); doc.setFont('helvetica', 'bold'); doc.setTextColor(15, 23, 42);
        doc.text("PADRÓN DE USUARIOS DEL CATASTRO DE RIEGO", 10, tableStartY - 3);
        doc.setTextColor(0, 0, 0); // Reset color
      }

      const headers = ['#', 'Código del Lote', 'Propietario / Regante', 'Identificación\n(Cédula / Clave)', 'Ubicación\n(Parroquia / Sector / Comunidad)', 'Área Total', 'Área Riego', 'Técnico', 'Fecha'];
      
      const rows: any[] = [];
      dataToRender.forEach((f, i) => {
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
          (f.area_riego && f.area_riego > 0) ? `${f.area_riego.toLocaleString('es-EC')} m²` : (f.area_total ? `${f.area_total.toLocaleString('es-EC')} m²` : '0 m²'),
          getNombreTecnico(f.creado_por),
          safeToDate(f.fecha_creacion).toLocaleDateString('es-EC'),
        ]);

        // Desglose de predios adicionales (tanto físicos como unificados virtuales)
        const adicionales = prediosAdicionalesData.filter((pa) => pa.ficha_id === f.id);
        adicionales.forEach((pa) => {
          // Buscamos si es una ficha virtual que tiene su respectivo registro original en las fichas para recuperar datos geográficos reales
          const fichaAdicionalFisica = allFichas.find((x) => x.id === pa.id_adicional);
          
          const ubicacionAdicional = [
            fichaAdicionalFisica?.parroquia,
            fichaAdicionalFisica?.sector,
            fichaAdicionalFisica?.comunidad
          ].filter(Boolean).join(' / ');

          const areaTotalAdicional = pa.area_total_otro || pa.area_lote_asignado_otro || 0;

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
              content: areaTotalAdicional > 0 ? `${areaTotalAdicional.toLocaleString('es-EC')} m²` : '0 m²', 
              styles: { textColor: [71, 85, 105], fillColor: [248, 250, 252], fontSize: 5.5, lineColor: [241, 245, 249] } 
            }, // Área Total
            { 
              content: (pa.area_riego_otro && pa.area_riego_otro > 0) ? `${pa.area_riego_otro.toLocaleString('es-EC')} m²` : (areaTotalAdicional > 0 ? `${areaTotalAdicional.toLocaleString('es-EC')} m²` : '0 m²'), 
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

    return doc;
  };

  const generatePDF = async () => {
    setGenerating('pdf');
    try {
      if (reportType === 'resumen_sectores') {
        const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
        const pageWidth = doc.internal.pageSize.getWidth();
        
        // Helper para cabecera de página
        const drawHeader = async (title: string) => {
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
          doc.setFontSize(8); doc.setFont('helvetica', 'bold');
          doc.text(title, pageWidth / 2, 26, { align: 'center' });
          doc.setFont('helvetica', 'normal');
          doc.text(`Generado: ${new Date().toLocaleDateString('es-EC')} | Catastro de Riego`, pageWidth / 2, 30, { align: 'center' });
        };

        // Generar 1 página para cada Sector
        for (let i = 0; i < 3; i++) {
          const sectorName = `Sector ${i + 1}`;
          if (i > 0) doc.addPage();
          await drawHeader(`CUADRO COMPARATIVO DE AVANCE - ${sectorName.toUpperCase()}`);
          
          const comunidadesSector = COMUNIDADES_POR_SECTOR[sectorName] || [];
          let totalMeta = 0;
          let totalLevantado = 0;
          
          const rows = comunidadesSector.map((comunidad) => {
            const meta = META_COMUNEROS[comunidad] || 0;
            const fichasCount = allFichas.filter(f => (f.comunidad || '').trim() === comunidad).length;
            totalMeta += meta;
            totalLevantado += fichasCount;
            const pct = meta > 0 ? (fichasCount / meta) * 100 : 0;
            return [
              comunidad,
              meta > 0 ? meta.toLocaleString('es-EC') : '-',
              fichasCount.toLocaleString('es-EC'),
              `${pct.toFixed(0)}%`
            ];
          });

          const pctTotal = totalMeta > 0 ? (totalLevantado / totalMeta) * 100 : 0;
          rows.push([
            'TOTAL SECTOR',
            totalMeta.toLocaleString('es-EC'),
            totalLevantado.toLocaleString('es-EC'),
            `${pctTotal.toFixed(1)}%`
          ]);

          autoTable(doc, {
            startY: 35,
            head: [['COMUNIDAD', 'CATASTRO BASE (# PLANIFICADO)', 'ENCUESTAS REALIZADAS (LEVANTADO)', 'PORCENTAJE AVANCE']],
            body: rows,
            theme: 'striped',
            headStyles: { fillColor: [30, 41, 59], fontSize: 8, fontStyle: 'bold', halign: 'center' },
            bodyStyles: { fontSize: 7.5, valign: 'middle' },
            columnStyles: {
              0: { cellWidth: 100, fontStyle: 'bold' },
              1: { cellWidth: 50, halign: 'center' },
              2: { cellWidth: 50, halign: 'center' },
              3: { cellWidth: 40, halign: 'center', fontStyle: 'bold' }
            },
            didParseCell: (dataCell) => {
              if (dataCell.row.index === rows.length - 1) {
                dataCell.cell.styles.fillColor = [226, 232, 240];
                dataCell.cell.styles.fontStyle = 'bold';
              }
            }
          });
        }

        // Página 4: Fichas Huérfanas
        doc.addPage();
        await drawHeader('AUDITORÍA DE FICHAS CON COMUNIDAD EN BLANCO (CÓDIGOS FID_1 PARA CORRECCIÓN)');
        
        const vacias = allFichas.filter((f) => !f.comunidad_original || (f.comunidad_original || '').trim() === '' || f.comunidad_original === 'None');
        
        const vaciasRows = vacias.map((f, i) => [
          i + 1,
          f.id,
          f.codigo_final || 'S/C',
          f.propietario,
          getNombreTecnico(f.creado_por),
          safeToDate(f.fecha_creacion).toLocaleDateString('es-EC')
        ]);

        autoTable(doc, {
          startY: 35,
          head: [['#', 'ID FÍSICO (fid_1)', 'CÓDIGO PREDIO', 'PROPIETARIO / REGANTE', 'TÉCNICO', 'FECHA REGISTRO']],
          body: vaciasRows,
          theme: 'grid',
          headStyles: { fillColor: [185, 28, 28], fontSize: 8, fontStyle: 'bold', halign: 'center' },
          bodyStyles: { fontSize: 7.5, valign: 'middle' },
          columnStyles: {
            0: { cellWidth: 15, halign: 'center' },
            1: { cellWidth: 35, halign: 'center', fontStyle: 'bold' },
            2: { cellWidth: 45, halign: 'center' },
            3: { cellWidth: 90 },
            4: { cellWidth: 50 },
            5: { cellWidth: 40, halign: 'center' }
          }
        });

        doc.save(`catastro_avance_sectores_${Date.now()}.pdf`);
        return;
      }

      const data = getFilteredFichas();
      const subtitles: Record<ReportType, string> = {
        general: 'REPORTE GENERAL DE FICHAS INVESTIGADAS',
        sector: `REPORTE POR SECTOR: ${filterSector || 'TODOS'}`,
        parroquia: `REPORTE POR PARROQUIA: ${filterParroquia || 'TODAS'}`,
        comunidad: `REPORTE POR COMUNIDAD: ${filterComunidad || 'TODAS'}`,
        tecnico: `REPORTE POR TÉCNICO: ${filterTecnico || 'TODOS'}`,
        fecha: `REPORTE POR FECHA: ${fechaDesde || '...'} al ${fechaHasta || '...'}`,
        ejecutivo: 'INFORME TÉCNICO EJECUTIVO',
        auditoria: 'REPORTE DE AUDITORÍA Y CONTROL DE CALIDAD',
        resumen_sectores: 'REPORTE DE COBERTURA Y AVANCE DE SECTORES',
      };
      
      const doc = await buildPdfDoc(data, subtitles[reportType], reportType === 'general');
      doc.save(`catastro_${reportType}_${Date.now()}.pdf`);
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Hubo un error al generar el PDF.');
    } finally {
      setGenerating(null);
    }
  };

  const generateAllComunidadesZIP = async () => {
    setGenerating('pdf');
    try {
      const zip = new JSZip();
      
      for (const com of COMUNIDADES) {
        const dataComunidad = fichas.filter((f) => (f.comunidad || '').trim() === com);
        
        if (dataComunidad.length > 0) {
          const doc = await buildPdfDoc(dataComunidad, `REPORTE POR COMUNIDAD: ${com}`, false);
          const pdfBlob = doc.output('blob');
          const fileName = `Reporte_${com.replace(/\s+/g, '_')}.pdf`;
          zip.file(fileName, pdfBlob);
        }
      }
      
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      saveAs(zipBlob, `Reportes_Todas_Las_Comunidades_${Date.now()}.zip`);
    } catch (error) {
      console.error('Error generating ZIP:', error);
      alert('Hubo un error al generar los reportes en lote.');
    } finally {
      setGenerating(null);
    }
  };

  const generateExcel = () => {
    setGenerating('excel');
    try {
      if (reportType === 'resumen_sectores') {
        const wb = XLSX.utils.book_new();
        
        ['Sector 1', 'Sector 2', 'Sector 3'].forEach((sectorName) => {
          const comunidadesSector = COMUNIDADES_POR_SECTOR[sectorName] || [];
          let totalMeta = 0;
          let totalLevantado = 0;
          
          const rows = comunidadesSector.map((comunidad) => {
            const meta = META_COMUNEROS[comunidad] || 0;
            const fichasCount = allFichas.filter(f => (f.comunidad || '').trim() === comunidad).length;
            totalMeta += meta;
            totalLevantado += fichasCount;
            const pct = meta > 0 ? (fichasCount / meta) * 100 : 0;
            return {
              'Comunidad': comunidad,
              'Catastro Base (Planificado)': meta,
              'Encuestas Realizadas (Levantado)': fichasCount,
              'Avance (%)': `${pct.toFixed(0)}%`
            };
          });

          const pctTotal = totalMeta > 0 ? (totalLevantado / totalMeta) * 100 : 0;
          rows.push({
            'Comunidad': 'TOTAL SECTOR',
            'Catastro Base (Planificado)': totalMeta,
            'Encuestas Realizadas (Levantado)': totalLevantado,
            'Avance (%)': `${pctTotal.toFixed(1)}%`
          });

          const ws = XLSX.utils.json_to_sheet(rows);
          XLSX.utils.book_append_sheet(wb, ws, sectorName);
        });

        const vacias = allFichas.filter((f) => !f.comunidad_original || (f.comunidad_original || '').trim() === '' || f.comunidad_original === 'None');
        const vaciasRows = vacias.map((f, i) => ({
          '#': i + 1,
          'ID Físico (fid_1)': f.id,
          'Código Predio': f.codigo_final || 'S/C',
          'Propietario / Regante': f.propietario,
          'Técnico': getNombreTecnico(f.creado_por),
          'Fecha Registro': safeToDate(f.fecha_creacion).toLocaleDateString('es-EC')
        }));
        
        const wsVacias = XLSX.utils.json_to_sheet(vaciasRows);
        XLSX.utils.book_append_sheet(wb, wsVacias, 'Fichas en Blanco');

        XLSX.writeFile(wb, `reporte_avance_sectores_${new Date().toISOString().split('T')[0]}.xlsx`);
        return;
      }

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
          const fichaAdicionalFisica = allFichas.find((x) => x.id === pa.id_adicional);

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
        { 'Métrica': 'Total Fichas Registradas en Campo (QField)', 'Valor': data.length },
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
    { id: 'resumen_sectores' as const, label: 'Avance de Sectores', icon: Layers, desc: 'Comparativo catastro vs levantamiento', color: '#10b981' },
    { id: 'sector' as const, label: 'Por Sector', icon: Layers, desc: 'Sectores de Investigación 1, 2 o 3', color: '#06b6d4' },
    { id: 'parroquia' as const, label: 'Por Parroquia', icon: MapPin, desc: 'Filtrar por parroquia', color: '#ec4899' },
    { id: 'comunidad' as const, label: 'Por Comunidad', icon: Building2, desc: `${COMUNIDADES.length} comunidades`, color: '#ec4899' },
    { id: 'tecnico' as const, label: 'Por Técnico', icon: Users, desc: 'Producción por investigador', color: '#f59e0b' },
    { id: 'fecha' as const, label: 'Por Fecha', icon: Calendar, desc: 'Rango de fechas personalizado', color: '#8b5cf6' },
    { id: 'ejecutivo' as const, label: 'Informe Ejecutivo', icon: FileText, desc: 'Informe técnico de avance y métricas', color: '#6366f1' },
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

      {reportType === 'ejecutivo' ? (
        <div className="space-y-6">
          <div
            className="rounded-xl border p-6 text-center max-w-2xl mx-auto"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
          >
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: 'rgba(99,102,241,0.1)' }}>
              <FileText className="w-7 h-7 text-indigo-400" />
            </div>
            
            <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
              Informe Técnico Ejecutivo
            </h3>
            <p className="text-xs mt-2 max-w-md mx-auto" style={{ color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              Este reporte consolida el estado actual del levantamiento catastral, la infraestructura de reservorios y métodos de riego, la fragmentación de tierras (minifundio) y la caracterización socio-productiva de las familias del SISTEMA DE RIEGO COMUNITARIO GUANGUILQUI POROTOG.
            </p>

            <div className="mt-6 flex flex-col items-center justify-center gap-3">
              <button
                onClick={() => window.open('/informe_reunion_tecnica.html?print=true', '_blank')}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-bold text-xs text-white bg-indigo-500 hover:bg-indigo-600 shadow-md hover:shadow-lg transition-all cursor-pointer"
              >
                <FileDown className="w-4 h-4" />
                Generar e Imprimir / Descargar PDF
              </button>
              <p className="text-[10px] mt-2 max-w-sm text-center" style={{ color: 'var(--text-muted)' }}>
                Nota: Al abrirse la nueva pestaña, aparecerá de forma automática la ventana de guardado. Elige <strong>"Guardar como PDF"</strong> para descargarlo con máxima calidad vectorial.
              </p>
            </div>
          </div>
        </div>
      ) : reportType === 'resumen_sectores' ? (
        <div className="space-y-6">
          <div className="flex justify-end gap-3 rounded-xl border p-4" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <button
              onClick={generatePDF}
              disabled={generating !== null}
              className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs text-white bg-indigo-500 hover:bg-indigo-600 shadow-md hover:shadow-lg transition-all cursor-pointer disabled:opacity-50"
            >
              <FileDown className="w-4 h-4" />
              {generating === 'pdf' ? 'Generando PDF...' : 'Descargar PDF (Avance)'}
            </button>
            <button
              onClick={generateExcel}
              disabled={generating !== null}
              className="flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs text-white bg-emerald-500 hover:bg-emerald-600 shadow-md hover:shadow-lg transition-all cursor-pointer disabled:opacity-50"
            >
              <FileSpreadsheet className="w-4 h-4" />
              {generating === 'excel' ? 'Generando Excel...' : 'Descargar Excel (Avance)'}
            </button>
          </div>

          <div className="grid grid-cols-1 gap-6">
            {['Sector 1', 'Sector 2', 'Sector 3'].map((sectorName) => {
              const comunidadesSector = COMUNIDADES_POR_SECTOR[sectorName] || [];
              
              let totalMetaSector = 0;
              let totalFichasSector = 0;
              
              const tableRows = comunidadesSector.map((comunidad) => {
                const meta = META_COMUNEROS[comunidad] || 0;
                const fichasCount = allFichas.filter(f => (f.comunidad || '').trim() === comunidad).length;
                
                totalMetaSector += meta;
                totalFichasSector += fichasCount;
                
                const pct = meta > 0 ? (fichasCount / meta) * 100 : 0;
                
                return {
                  comunidad,
                  meta,
                  fichasCount,
                  pct
                };
              }).sort((a, b) => b.fichasCount - a.fichasCount);
              
              const pctSector = totalMetaSector > 0 ? (totalFichasSector / totalMetaSector) * 100 : 0;
              
              return (
                <div 
                  key={sectorName}
                  className="rounded-xl border p-5 space-y-4"
                  style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <h3 className="text-base font-bold" style={{ color: 'var(--text-heading)' }}>
                        CUADRO RESUMEN {sectorName.toUpperCase()}
                      </h3>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        Comunidades pertenecientes al área de investigación del {sectorName}
                      </p>
                    </div>
                    
                    <div className="flex items-center gap-6 text-xs text-right self-end md:self-auto">
                      <div>
                        <p style={{ color: 'var(--text-muted)' }}>PLANIFICADO</p>
                        <p className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>{totalMetaSector.toLocaleString('es-EC')}</p>
                      </div>
                      <div className="w-px h-8 bg-gray-700" />
                      <div>
                        <p style={{ color: 'var(--text-muted)' }}>LEVANTADO</p>
                        <p className="text-base font-bold text-blue-400">{totalFichasSector.toLocaleString('es-EC')}</p>
                      </div>
                      <div className="w-px h-8 bg-gray-700" />
                      <div>
                        <p style={{ color: 'var(--text-muted)' }}>COBERTURA</p>
                        <p className={`text-base font-bold ${pctSector >= 90 ? 'text-emerald-400' : 'text-blue-400'}`}>
                          {pctSector.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left border-collapse">
                      <thead>
                        <tr className="border-b" style={{ borderColor: 'var(--border-color)' }}>
                          <th className="py-2.5 font-bold" style={{ color: 'var(--text-muted)' }}>COMUNIDAD</th>
                          <th className="py-2.5 font-bold text-center" style={{ color: 'var(--text-muted)' }}>CATASTRO BASE (#)</th>
                          <th className="py-2.5 font-bold text-center" style={{ color: 'var(--text-muted)' }}>ENCUESTAS REALIZADAS</th>
                          <th className="py-2.5 font-bold" style={{ color: 'var(--text-muted)' }}>PORCENTAJE AVANCE</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tableRows.map((r) => (
                          <tr 
                            key={r.comunidad} 
                            className="border-b transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                            style={{ borderColor: 'var(--border-color)' }}
                          >
                            <td className="py-2.5 font-medium" style={{ color: 'var(--text-primary)' }}>{r.comunidad}</td>
                            <td className="py-2.5 text-center font-semibold" style={{ color: 'var(--text-secondary)' }}>
                              {r.meta > 0 ? r.meta.toLocaleString('es-EC') : '-'}
                            </td>
                            <td className="py-2.5 text-center font-bold text-blue-400">{r.fichasCount.toLocaleString('es-EC')}</td>
                            <td className="py-2.5">
                              <div className="flex items-center gap-2">
                                <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
                                  <div 
                                    className={`h-full rounded-full ${r.pct >= 90 ? 'bg-emerald-500' : 'bg-blue-500'}`}
                                    style={{ width: `${Math.min(r.pct, 100)}%` }}
                                  />
                                </div>
                                <span className="font-semibold w-10 text-right shrink-0" style={{ color: r.pct >= 90 ? '#10b981' : 'var(--text-secondary)' }}>
                                  {r.pct.toFixed(0)}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* Fichas con Comunidad Vacía */}
          <div 
            className="rounded-xl border border-red-500/30 p-5 space-y-4"
            style={{ background: 'rgba(239, 68, 68, 0.02)', boxShadow: 'var(--shadow-card)' }}
          >
            <div>
              <h3 className="text-base font-bold text-red-400 flex items-center gap-2">
                ⚠️ FICHAS CON COMUNIDAD EN BLANCO (CÓDIGOS FID_1 PARA CORRECCIÓN)
              </h3>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                Los técnicos de campo deben buscar estas 7 fichas en sus dispositivos o en QGIS por su ID físico (fid_1) para corregir y asignarles comunidad.
              </p>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-red-500/10">
                    <th className="py-2.5 font-bold" style={{ color: 'var(--text-muted)' }}>ID FÍSICO (`fid_1`)</th>
                    <th className="py-2.5 font-bold" style={{ color: 'var(--text-muted)' }}>CÓDIGO PREDIO</th>
                    <th className="py-2.5 font-bold" style={{ color: 'var(--text-muted)' }}>PROPIETARIO / REGANTE</th>
                    <th className="py-2.5 font-bold" style={{ color: 'var(--text-muted)' }}>TÉCNICO</th>
                    <th className="py-2.5 font-bold" style={{ color: 'var(--text-muted)' }}>FECHA REGISTRO</th>
                  </tr>
                </thead>
                <tbody>
                  {allFichas
                    .filter((f) => !f.comunidad_original || (f.comunidad_original || '').trim() === '' || f.comunidad_original === 'None')
                    .map((f) => (
                      <tr 
                        key={f.id} 
                        className="border-b border-red-500/5 transition-colors hover:bg-red-500/5"
                      >
                        <td className="py-2.5 font-bold text-red-400">#{f.id}</td>
                        <td className="py-2.5 font-semibold" style={{ color: 'var(--text-primary)' }}>{f.codigo_final || 'S/C'}</td>
                        <td className="py-2.5 font-medium" style={{ color: 'var(--text-primary)' }}>{f.propietario}</td>
                        <td className="py-2.5" style={{ color: 'var(--text-secondary)' }}>{getNombreTecnico(f.creado_por)}</td>
                        <td className="py-2.5 text-gray-500">{safeToDate(f.fecha_creacion).toLocaleDateString('es-EC')}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : reportType !== 'auditoria' ? (
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
                  {['Sector 1', 'Sector 2', 'Sector 3'].map((s) => <option key={s} value={s}>{s}</option>)}
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
                  <option value="">
                    {filtros.sectorInv 
                      ? `Comunidades del ${filtros.sectorInv} (${(COMUNIDADES_POR_SECTOR[filtros.sectorInv] || []).length})`
                      : `Todas las comunidades (${COMUNIDADES.length})`
                    }
                  </option>
                  {(filtros.sectorInv 
                    ? (COMUNIDADES_POR_SECTOR[filtros.sectorInv] || []) 
                    : COMUNIDADES
                  ).map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              )}
              {reportType === 'tecnico' && (
                <select value={filterTecnico} onChange={(e) => setFilterTecnico(e.target.value)}
                  className="px-3 py-2 rounded-lg text-sm cursor-pointer min-w-[180px]" style={selectStyle}>
                  <option value="">Todos los técnicos</option>
                  {tecnicosUnicos.map((nombre) => (
                    <option key={nombre} value={nombre}>{nombre}</option>
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
          <div className={`grid grid-cols-1 sm:grid-cols-${reportType === 'comunidad' ? '3' : '2'} gap-4`}>
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

            {/* ZIP Masivo (Solo Comunidad) */}
            {reportType === 'comunidad' && (
              <button
                onClick={generateAllComunidadesZIP}
                disabled={generating !== null}
                className="group relative flex items-center gap-4 p-5 rounded-xl border-2 text-left transition-all disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed overflow-hidden"
                style={{
                  background: 'var(--bg-card)',
                  borderColor: generating === 'pdf' ? '#ec489980' : 'var(--border-color)',
                }}
              >
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ background: 'linear-gradient(135deg, rgba(236,72,153,0.04), transparent)' }} />
                <div className="relative w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: 'rgba(236,72,153,0.1)' }}>
                  {generating === 'pdf' ? (
                    <Loader2 className="w-6 h-6 text-pink-400 animate-spin" />
                  ) : (
                    <Building2 className="w-6 h-6 text-pink-400" />
                  )}
                </div>
                <div className="relative flex-1 min-w-0">
                  <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    Lote ZIP (Todas)
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    Exportar 22 PDFs en un ZIP
                  </p>
                </div>
                <Download className="w-5 h-5 shrink-0 opacity-30 group-hover:opacity-60 transition-opacity" style={{ color: 'var(--text-secondary)' }} />
              </button>
            )}

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
                  <div className="p-8 border rounded-xl text-center" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: 'rgba(16,185,129,0.1)' }}>
                        <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Base de Datos Conciliada al 100%</p>
                        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>No existen fichas con unificación virtual activa. Los datos de la web coinciden exactamente con los datos locales de QField.</p>
                      </div>
                    </div>
                  </div>
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
