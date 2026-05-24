import { useState } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { ChevronRight, ChevronLeft, Save, Leaf, FileDown } from 'lucide-react';
import { Step1Propietario } from './steps/Step1Propietario';
import { Step2PredioRiego } from './steps/Step2PredioRiego';
import { Step3Servicios } from './steps/Step3Servicios';
import { Step4Produccion } from './steps/Step4Produccion';
import { Step5Encuesta } from './steps/Step5Encuesta';
import { Step6Finalizacion } from './steps/Step6Finalizacion';
import { generatePadronPDF } from '../lib/pdfGenerator';
import { generateAprobacionVacia } from '../lib/pdfAprobacion';

const steps = [
  { id: 1, title: 'Datos del Propietario' },
  { id: 2, title: 'Predio y Riego' },
  { id: 3, title: 'Servicios y Ubicación' },
  { id: 4, title: 'Sistema de Producción' },
  { id: 5, title: 'Encuesta Junta de Agua' },
  { id: 6, title: 'Finalización' },
];

export function PadronWizard() {
  const [currentStep, setCurrentStep] = useState(1);
  const methods = useForm({
    defaultValues: {
      // Propietario
      claveCatastral: '',
      parroquia: 'CANGAHUA',
      comunidad: 'CARRERA',
      sector: '',
      nombres: '',
      apellidos: '',
      cedula: '',
      tenencia: 'Escritura',
      telefonoCelular: '',
      telefonoCasa: '',
      hijosHombres: 0,
      hijosMujeres: 0,
      instruccion: 'primaria',
      
      // Riego
      organizacionRiego: 'DESCONOCE',
      claveCatastralPredio: '',
      codigoPredio: 'NSC',
      numPredio: '1',
      sectorComunidad: 'ALTA',
      canal: 'SAN JOAQUIN',
      caudal: 'NSC',
      tipoCaudal: '',
      unidadArea: 'ha',
      areaRiego: 0,
      areaTotal: 0,
      metodoInundacion: 0,
      metodoAspersion: 0,
      metodoGoteo: 0,
      frecuenciaRiego: 'semanal',
      diasRiego: 0,
      horasTurno: 0,
      valorTarifa: 0,
      tipoTarifa: 'por turno',
      tieneReservorio: 'No',

      // Servicios
      aguaConsumo: false,
      energiaElectrica: false,
      materialVivienda: 'ADOBE',

      coordX: '',
      coordY: '',
      cota: '',

      // Produccion (simplified for now)
      cultivos: [],
      animales: [],
      usoSoberania: 50,
      usoProductivas: 50,

      // Encuesta
      tieneEstatutos: 'si',
      tieneReglamentos: 'si',
      conocePresa: 'si',
      comoSeElige: '',
      nombrePresidente: '',
      quienOpera: '',
      aniosSistema: '',
      kmCanal: '',
      recibioCapacitacion: 'no',
      leGustariaCapacitacion: 'si',
      temasCapacitacion: '',

      // Emplazamiento
      emplazamiento: '',
      investigadoPor: 'Téc. Ing. Ramiro Quilca – CONSORCIO CAYAMBE SPT',
      fecha: new Date().toISOString().split('T')[0],
      observaciones: ''
    }
  });

  const onSubmit = (data: Record<string, unknown>) => {
    console.log(data);
    generatePadronPDF(data);
  };

  const nextStep = () => setCurrentStep((prev) => Math.min(prev + 1, steps.length));
  const prevStep = () => setCurrentStep((prev) => Math.max(prev - 1, 1));

  return (
    <div className="min-h-screen bg-agri-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-agri-700 px-6 py-6 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Leaf className="h-7 w-7 text-agri-100" />
              <div>
                <h1 className="text-xl font-bold">Padrón de Usuarios de Riego</h1>
                <p className="text-agri-100 opacity-80 text-sm">Sistema de Riego Comunitario Guanguilqui Porotog</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => generateAprobacionVacia()}
              className="flex items-center gap-2 px-4 py-2 bg-white/15 hover:bg-white/25 rounded-lg text-sm font-medium transition-colors border border-white/30"
            >
              <FileDown className="w-4 h-4" />
              Descargar Formulario Oficial (Aprobación)
            </button>
          </div>
        </div>

        {/* Stepper Indicator */}
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 overflow-x-auto">
          <nav aria-label="Progress">
            <ol role="list" className="flex items-center space-x-4 min-w-max">
              {steps.map((step, stepIdx) => (
                <li key={step.title} className="flex items-center">
                  <span className={`
                    flex items-center justify-center w-8 h-8 rounded-full font-medium text-sm
                    ${currentStep === step.id ? 'bg-agri-600 text-white' : 
                      currentStep > step.id ? 'bg-agri-100 text-agri-700' : 'bg-gray-200 text-gray-500'}
                  `}>
                    {step.id}
                  </span>
                  <span className={`ml-3 text-sm font-medium ${currentStep === step.id ? 'text-agri-700' : 'text-gray-500'}`}>
                    {step.title}
                  </span>
                  {stepIdx !== steps.length - 1 ? (
                    <ChevronRight className="w-5 h-5 ml-4 text-gray-300" aria-hidden="true" />
                  ) : null}
                </li>
              ))}
            </ol>
          </nav>
        </div>

        {/* Form Content */}
        <div className="p-6 sm:p-8">
          <FormProvider {...methods}>
            <form onSubmit={methods.handleSubmit(onSubmit)}>
              
              <div className="min-h-[400px]">
                {currentStep === 1 && <Step1Propietario />}
                {currentStep === 2 && <Step2PredioRiego />}
                {currentStep === 3 && <Step3Servicios />}
                {currentStep === 4 && <Step4Produccion />}
                {currentStep === 5 && <Step5Encuesta />}
                {currentStep === 6 && <Step6Finalizacion />}
              </div>

              {/* Navigation Buttons */}
              <div className="mt-8 flex justify-between pt-6 border-t border-gray-200">
                <button
                  type="button"
                  onClick={prevStep}
                  disabled={currentStep === 1}
                  className={`flex items-center px-4 py-2 text-sm font-medium rounded-md shadow-sm border border-gray-300 
                    ${currentStep === 1 ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
                >
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Anterior
                </button>
                
                {currentStep < steps.length ? (
                  <button
                    type="button"
                    onClick={nextStep}
                    className="flex items-center px-6 py-2 text-sm font-medium rounded-md shadow-sm text-white bg-agri-600 hover:bg-agri-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-agri-500 transition-colors"
                  >
                    Siguiente
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    className="flex items-center px-6 py-2 text-sm font-medium rounded-md shadow-sm text-white bg-agri-600 hover:bg-agri-700 transition-colors"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    Generar Padrón PDF
                  </button>
                )}
              </div>

            </form>
          </FormProvider>
        </div>
      </div>
    </div>
  );
}
