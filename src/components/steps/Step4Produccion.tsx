import { useFormContext, useFieldArray, useWatch } from "react-hook-form";

// ── Helper: indicador visual de suma de porcentajes ──────────────────────────
function SumIndicator({ value }: { value: number }) {
  const ok = value === 100;
  const over = value > 100;
  return (
    <span
      className={`ml-1 text-xs font-bold px-1.5 py-0.5 rounded ${
        ok ? "bg-green-100 text-green-700" : over ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
      }`}
    >
      {value}% {ok ? "✓" : over ? "⚠ >100%" : "≠100%"}
    </span>
  );
}

// ── Fila de cultivo ──────────────────────────────────────────────────────────
function CultivoRow({ index, onRemove }: { index: number; onRemove: () => void }) {
  const { register, control } = useFormContext();
  const vals = useWatch({ control, name: `cultivos.${index}` }) as Record<string, number> | undefined;
  const total =
    Number(vals?.pctAuto ?? 0) +
    Number(vals?.pctVenta ?? 0) +
    Number(vals?.pctSemilla ?? 0) +
    Number(vals?.pctAlimAnimal ?? 0) +
    Number(vals?.pctTransform ?? 0);

  return (
    <tr className="bg-white hover:bg-green-50/50 transition-colors">
      <td className="p-2">
        <input
          {...register(`cultivos.${index}.nombre`)}
          placeholder="Ej. Papas"
          className="w-full text-sm p-1.5 border border-gray-300 rounded focus:ring-green-500 focus:border-green-500"
        />
      </td>
      <td className="p-2 w-28">
        <input
          type="number"
          {...register(`cultivos.${index}.superficie`)}
          placeholder="m²"
          className="w-full text-sm p-1.5 border border-gray-300 rounded focus:ring-green-500 focus:border-green-500"
        />
      </td>
      <td className="p-2 text-center">
        <input
          type="checkbox"
          {...register(`cultivos.${index}.esPrincipal`)}
          className="h-4 w-4 text-green-600 rounded border-gray-300 cursor-pointer"
        />
      </td>
      {(["pctAuto", "pctVenta", "pctSemilla", "pctAlimAnimal", "pctTransform"] as const).map((field) => (
        <td key={field} className="p-1 text-center border-l border-green-100 w-14">
          <input
            type="number"
            min={0}
            max={100}
            {...register(`cultivos.${index}.${field}`, { valueAsNumber: true })}
            placeholder="0"
            className="w-full text-xs p-1 border border-gray-300 rounded text-center focus:ring-green-500 focus:border-green-500"
          />
        </td>
      ))}
      <td className="p-2 text-center">
        <SumIndicator value={total} />
      </td>
      <td className="p-2 text-center">
        <button
          type="button"
          onClick={onRemove}
          className="text-red-500 font-bold p-1.5 hover:bg-red-100 rounded transition-colors"
          title="Eliminar"
        >
          ✕
        </button>
      </td>
    </tr>
  );
}

// ── Fila de animal ───────────────────────────────────────────────────────────
function AnimalRow({ index, onRemove }: { index: number; onRemove: () => void }) {
  const { register, control } = useFormContext();
  const vals = useWatch({ control, name: `animales.${index}` }) as Record<string, number> | undefined;
  const total =
    Number(vals?.pctAuto ?? 0) +
    Number(vals?.pctVenta ?? 0) +
    Number(vals?.pctTransform ?? 0);

  return (
    <tr className="bg-white hover:bg-amber-50/50 transition-colors">
      <td className="p-2">
        <input
          {...register(`animales.${index}.tipo`)}
          placeholder="Ej. Vacas, Cuyes"
          className="w-full text-sm p-1.5 border border-gray-300 rounded focus:ring-amber-500 focus:border-amber-500"
        />
      </td>
      <td className="p-2 w-28">
        <input
          type="number"
          {...register(`animales.${index}.cantidad`)}
          placeholder="Cant."
          className="w-full text-sm p-1.5 border border-gray-300 rounded focus:ring-amber-500 focus:border-amber-500"
        />
      </td>
      {(["pctAuto", "pctVenta", "pctTransform"] as const).map((field) => (
        <td key={field} className="p-1 text-center border-l border-amber-100 w-14">
          <input
            type="number"
            min={0}
            max={100}
            {...register(`animales.${index}.${field}`, { valueAsNumber: true })}
            placeholder="0"
            className="w-full text-xs p-1 border border-gray-300 rounded text-center focus:ring-amber-500 focus:border-amber-500"
          />
        </td>
      ))}
      <td className="p-2 text-center">
        <SumIndicator value={total} />
      </td>
      <td className="p-2 text-center">
        <button
          type="button"
          onClick={onRemove}
          className="text-red-500 font-bold p-1.5 hover:bg-red-100 rounded transition-colors"
          title="Eliminar"
        >
          ✕
        </button>
      </td>
    </tr>
  );
}

// ── Componente principal ─────────────────────────────────────────────────────
export function Step4Produccion() {
  const { register, control } = useFormContext();

  const { fields: cultivFields, append: appendCultivo, remove: removeCultivo } = useFieldArray({
    control,
    name: "cultivos",
  });

  const { fields: animFields, append: appendAnimal, remove: removeAnimal } = useFieldArray({
    control,
    name: "animales",
  });

  return (
    <div className="space-y-8">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl font-semibold text-gray-800">4. Datos del Sistema de Producción</h2>
        <p className="text-sm text-gray-500 mt-1">
          Sistemas agrícolas y pecuarios. Los porcentajes de destino de cada ítem deben sumar <strong>100 %</strong>.
        </p>
      </div>

      <div className="space-y-8">
        {/* ── Agrícola ── */}
        <div className="bg-green-50 p-4 md:p-6 rounded-xl border border-green-100 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-green-800">1. Sistema de Producción Agrícola</h3>
            <button
              type="button"
              onClick={() =>
                appendCultivo({
                  nombre: "",
                  superficie: "",
                  esPrincipal: false,
                  pctAuto: 0,
                  pctVenta: 0,
                  pctSemilla: 0,
                  pctAlimAnimal: 0,
                  pctTransform: 0,
                })
              }
              className="text-sm bg-green-600 text-white px-3 py-1.5 rounded hover:bg-green-700 shadow transition-colors"
            >
              + Agregar Cultivo
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[820px]">
              <thead>
                <tr className="border-green-200 text-xs text-green-800 uppercase tracking-wider">
                  <th className="py-2 px-2 font-semibold align-bottom border-b" rowSpan={2}>Cultivo</th>
                  <th className="py-2 px-2 font-semibold align-bottom border-b" rowSpan={2}>Superf. (m²)</th>
                  <th className="py-2 px-2 font-semibold text-center align-bottom border-b" rowSpan={2}>Principal</th>
                  <th className="py-1 px-2 font-semibold text-center border-l border-b border-green-200" colSpan={5}>
                    Destino de la Producción (%)
                  </th>
                  <th className="py-2 px-2 font-semibold text-center align-bottom border-b" rowSpan={2}>Total</th>
                  <th className="py-2 px-2 border-b" rowSpan={2}></th>
                </tr>
                <tr className="border-b border-green-200 text-[10px] text-green-700 uppercase tracking-wider h-28">
                  {["Autoconsumo", "Venta", "Semilla", "Alim. Animal", "Transform."].map((h) => (
                    <th key={h} className="p-1 text-center border-l border-green-200 align-bottom w-14">
                      <div className="mx-auto" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>
                        {h}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-green-100">
                {cultivFields.map((item, index) => (
                  <CultivoRow key={item.id} index={index} onRemove={() => removeCultivo(index)} />
                ))}
              </tbody>
            </table>
            {cultivFields.length === 0 && (
              <div className="p-4 text-sm text-green-700 italic text-center bg-white rounded-b-lg border-t border-green-100">
                No hay cultivos registrados. Presione &quot;+ Agregar Cultivo&quot;.
              </div>
            )}
          </div>
        </div>

        {/* ── Pecuario ── */}
        <div className="bg-amber-50 p-4 md:p-6 rounded-xl border border-amber-100 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-amber-800">2. Sistema de Producción Pecuario</h3>
            <button
              type="button"
              onClick={() => appendAnimal({ tipo: "", cantidad: "", pctAuto: 0, pctVenta: 0, pctTransform: 0 })}
              className="text-sm bg-amber-600 text-white px-3 py-1.5 rounded hover:bg-amber-700 shadow transition-colors"
            >
              + Agregar Animales
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[600px]">
              <thead>
                <tr className="border-amber-200 text-xs text-amber-800 uppercase tracking-wider">
                  <th className="py-2 px-2 font-semibold align-bottom border-b" rowSpan={2}>Animales</th>
                  <th className="py-2 px-2 font-semibold align-bottom border-b" rowSpan={2}>Número / Cantidad</th>
                  <th className="py-1 px-2 font-semibold text-center border-l border-b border-amber-200" colSpan={3}>
                    Destino de la Producción (%)
                  </th>
                  <th className="py-2 px-2 font-semibold text-center align-bottom border-b" rowSpan={2}>Total</th>
                  <th className="py-2 px-2 border-b" rowSpan={2}></th>
                </tr>
                <tr className="border-b border-amber-200 text-[10px] text-amber-700 uppercase tracking-wider h-28">
                  {["Autoconsumo", "Venta", "Transform."].map((h) => (
                    <th key={h} className="p-1 text-center border-l border-amber-200 align-bottom w-14">
                      <div className="mx-auto" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>
                        {h}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-amber-100">
                {animFields.map((item, index) => (
                  <AnimalRow key={item.id} index={index} onRemove={() => removeAnimal(index)} />
                ))}
              </tbody>
            </table>
            {animFields.length === 0 && (
              <div className="p-4 text-sm text-amber-700 italic text-center bg-white rounded-b-lg border-t border-amber-100">
                No hay animales registrados. Presione &quot;+ Agregar Animales&quot;.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Uso del Agua ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-gray-100">
        <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
          <label className="block text-sm font-bold text-blue-800 mb-3">3. Uso del Agua (%)</label>
          <div className="space-y-3">
            {[
              { label: "Soberanía Alimentaria", field: "usoSoberania" },
              { label: "Actividades Productivas", field: "usoProductivas" },
            ].map(({ label, field }) => (
              <div
                key={field}
                className="flex items-center justify-between text-sm bg-white p-2 border border-blue-100 rounded shadow-sm"
              >
                <span className="text-blue-900 font-medium">{label}</span>
                <div className="flex items-center">
                  <input
                    type="number"
                    max={100}
                    {...register(field)}
                    className="w-16 p-1 border border-gray-300 rounded text-right focus:ring-blue-500 focus:border-blue-500"
                  />
                  <span className="ml-2 text-gray-500">%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
