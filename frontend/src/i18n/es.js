// Spanish dictionary — neutral, professional Spanish (no regional slang, no
// voseo). Same key set as en.js; any missing key falls back to English at
// lookup time (see LanguageContext.jsx).
export default {
  // App shell
  'app.subtitle': 'Divide los gastos grupales y controla quién le debe a quién, en todos los eventos.',

  // Language switcher
  'language.code': 'ES',
  'language.switchToSpanish': 'Cambiar idioma a español',
  'language.switchToEnglish': 'Cambiar idioma a inglés',

  // Top-level tab navigation
  'tabs.ariaLabel': 'Secciones principales',
  'tabs.participants': 'Participantes',
  'tabs.events': 'Eventos',
  'tabs.balances': 'Balances',

  // "How it works" guide
  'guide.toggle': 'Cómo funciona',
  'guide.step1': 'Agrega participantes — las personas que dividen los gastos (pestaña Participantes)',
  'guide.step2': 'Crea o elige un evento — por ejemplo, un asado o un viaje (pestaña Eventos)',
  'guide.step3': 'Agrega esos participantes al evento',
  'guide.step4': 'Sube el recibo — su foto, quién pagó y el monto total',
  'guide.step5': 'Enumera cada producto con su precio (la cantidad es opcional, solo informativa)',
  'guide.step6': 'Divide cada producto entre quienes lo consumieron',
  'guide.step7': 'Consulta el total que cada persona debe o le deben (pestaña Balances)',
  'guide.note':
    'Quién pagó y el total son los datos que permiten a la aplicación calcular quién le debe a quién — no los omitas.',

  // Shared / common strings
  'common.delete': 'Eliminar',
  'common.deleting': 'Eliminando…',
  'common.close': 'Cerrar',
  'common.remove': 'Quitar',
  'common.discard': 'Descartar',
  'common.refresh': 'Actualizar',
  // Kept as "0.00" (not "0,00") even in Spanish: this is a placeholder for a
  // native <input type="number">, which always parses/displays with a period
  // regardless of UI language — a comma would look like a valid hint but be
  // rejected by the input itself.
  'common.amountPlaceholder': '0.00',

  // Participants tab
  'participants.title': 'Participantes',
  'participants.hint': 'Todas las personas que pueden deber o que les pueden deber, en todos los eventos.',
  'participants.form.nameLabel': 'Nombre',
  'participants.form.namePlaceholder': 'ej. Alex Rivera',
  'participants.form.submit': 'Agregar participante',
  'participants.form.submitting': 'Agregando…',
  'participants.loading': 'Cargando participantes…',
  'participants.empty': 'Todavía no hay participantes. Agrega el primer nombre arriba para iniciar un registro.',
  'participants.joined': 'se unió el {date}',
  'participants.confirmDelete': '¿Eliminar al participante "{name}"? Esta acción no se puede deshacer.',

  // Events tab
  'events.title': 'Eventos',
  'events.hint': 'Un asado, un viaje, una cuenta compartida — una página de registro por evento.',
  'events.form.nameLabel': 'Nombre del evento',
  'events.form.namePlaceholder': 'ej. Fin de semana en la cabaña',
  'events.form.dateLabel': 'Fecha (opcional)',
  'events.form.submit': 'Crear evento',
  'events.form.submitting': 'Creando…',
  'events.loading': 'Cargando eventos…',
  'events.empty': 'Todavía no hay eventos. Crea uno arriba para empezar a dividir una cuenta.',
  'events.confirmDelete':
    '¿Eliminar el evento "{name}"? Esto también elimina sus recibos e ítems. Esta acción no se puede deshacer.',

  // Event detail
  'eventDetail.loading': 'Cargando evento…',
  'eventDetail.backToEvents': '← Volver a eventos',
  'eventDetail.notFound': 'Evento no encontrado.',
  'eventDetail.participantsTitle': 'Participantes de este evento',
  'eventDetail.noParticipants':
    'Todavía no hay nadie vinculado. Agrega un participante abajo antes de subir un recibo.',
  'eventDetail.loadingParticipants': 'Cargando participantes…',
  'eventDetail.addParticipantLabel': 'Agregar participante',
  'eventDetail.selectSomeone': 'Selecciona a alguien…',
  'eventDetail.addToEvent': 'Agregar al evento',
  'eventDetail.addingParticipant': 'Agregando…',
  'eventDetail.everyoneLinked': 'Todos ya están vinculados a este evento.',
  'eventDetail.uploadReceiptTitle': 'Subir un recibo',
  'eventDetail.receiptsTitle': 'Recibos de este evento',
  'eventDetail.loadingReceipts': 'Cargando recibos…',
  'eventDetail.noReceipts': 'Todavía no se subió ningún recibo para este evento.',
  'eventDetail.receiptLabel': 'Recibo #{id} — pagado por {payer}',

  // Receipt upload form
  'receiptUpload.noParticipants': 'Agrega al menos un participante a este evento antes de subir un recibo.',
  'receiptUpload.imageLabel': 'Imagen del recibo',
  'receiptUpload.paidByLabel': 'Pagado por',
  'receiptUpload.selectPayer': 'Selecciona quién pagó…',
  'receiptUpload.totalLabel': 'Monto total',
  'receiptUpload.submit': 'Subir recibo',
  'receiptUpload.submitting': 'Subiendo…',

  // Receipt detail
  'receiptDetail.loading': 'Cargando recibo…',
  'receiptDetail.backToEvent': '← Volver al evento',
  'receiptDetail.notFound': 'Recibo no encontrado.',
  'receiptDetail.title': 'Recibo #{id}',
  'receiptDetail.hint': 'Captura cada ítem y luego asígnalo a quien lo consumió.',
  'receiptDetail.addItemTitle': 'Agregar un ítem',
  'receiptDetail.itemsTitle': 'Ítems de este recibo',
  'receiptDetail.reconcile.matchHeadline': 'Los ítems coinciden con el total del recibo.',
  'receiptDetail.reconcile.mismatchHeadline': 'Los ítems todavía no coinciden',
  'receiptDetail.reconcile.detailBase': 'Ítems capturados hasta ahora: {sum} de {total} en total',
  'receiptDetail.reconcile.mismatchSuffix': ' — {direction} por {amount}. Agrega o corrige ítems hasta que coincidan.',
  'receiptDetail.reconcile.over': 'de más',
  'receiptDetail.reconcile.under': 'de menos',

  // Item form (manual capture)
  'itemForm.nameLabel': 'Ítem',
  'itemForm.namePlaceholder': 'ej. Hamburguesa con queso',
  'itemForm.priceLabel': 'Precio',
  'itemForm.submit': 'Agregar ítem',
  'itemForm.submitting': 'Agregando…',

  // Item list
  'itemList.empty': 'Todavía no se capturó ningún ítem. Agrega el primero arriba.',
  'itemList.unassigned': 'Sin asignar',
  'itemList.assignmentEntry': '{name} ({amount})',
  'itemList.quantitySuffix': ' × {quantity}',
  'itemList.assign': 'Asignar',

  // Item assignment panel
  'itemAssignment.evenSplit': 'Dividir en partes iguales',
  'itemAssignment.save': 'Guardar asignación',
  'itemAssignment.saving': 'Guardando…',
  'itemAssignment.mismatch':
    'Las partes suman {total}, no 1.0. Aun así puedes guardar — el servidor tiene la última palabra.',

  // Extraction review (Phase 2)
  'extraction.title': 'Extraer ítems de la foto',
  'extraction.hint':
    'Lee la imagen del recibo subida y propone una lista de ítems para que la revises — no se guarda nada hasta que confirmes abajo.',
  'extraction.extractButton': 'Extraer ítems de la foto',
  'extraction.extracting': 'Extrayendo…',
  'extraction.manualFallbackHint': 'La captura manual de abajo sigue funcionando — agrega los ítems a mano.',
  'extraction.reviewTitle': 'Revisar ítems extraídos',
  'extraction.receiptTotalOnFile': 'Total del recibo registrado: {total}',
  'extraction.taxIncludedHint':
    'Se detectó un IVA de {total} y ya fue incluido de forma proporcional en los precios de los ítems de arriba — nadie debe pagarlo por separado.',
  'extraction.noRowsLeft': 'No quedan filas para guardar. Descarta, o vuelve a extraer.',
  'extraction.table.description': 'Descripción',
  'extraction.table.price': 'Precio',
  'extraction.table.qty': 'Cant.',
  'extraction.table.descriptionAriaLabel': 'Descripción del ítem',
  'extraction.table.priceAriaLabel': 'Precio del ítem',
  'extraction.quantityHint':
    'La cantidad se muestra solo como referencia — el precio ya refleja el total de esa línea completa, y el paso de guardado no almacena la cantidad por separado, así que los balances no se ven afectados.',
  'extraction.rowsInvalidHint':
    'Cada fila necesita una descripción y un precio mayor que 0 antes de poder guardar — corrige o quita la fila con el problema.',
  'extraction.addItemsButtonOne': 'Agregar {count} ítem al recibo',
  'extraction.addItemsButtonOther': 'Agregar {count} ítems al recibo',
  'extraction.saving': 'Guardando…',
  'extraction.partialSaveHint':
    'Es posible que el guardado se haya completado parcialmente — revisa la lista de ítems de abajo y quita las filas que ya se hayan agregado antes de volver a intentarlo.',

  // Balances tab
  'balances.title': 'Balances',
  'balances.hint': 'La tinta negra significa que te deben. La tinta roja significa que debes.',
  'balances.byEventTitle': 'Por evento',
  'balances.loadingEvents': 'Cargando eventos…',
  'balances.noEvents': 'Todavía no hay eventos — crea uno para ver su balance.',
  'balances.selectEvent': 'Selecciona un evento…',
  'balances.loadingEventBalances': 'Cargando balances…',
  'balances.noEventBalances': 'Todavía no hay balances para este evento.',
  'balances.table.participant': 'Participante',
  'balances.table.paid': 'Pagado',
  'balances.table.consumed': 'Consumido',
  'balances.table.net': 'Neto',
  'balances.overallTitle': 'General, en todos los eventos',
  'balances.loadingOverall': 'Cargando balance general…',
  'balances.nothingToSettle': 'Todavía no hay nada que saldar.',
  'balances.dangerZone.title': 'Zona de peligro',
  'balances.dangerZone.hint': 'Borra de forma permanente todos los participantes, eventos, recibos y balances.',
  'balances.dangerZone.deleteButton': 'Eliminar todos los datos',
  'balances.dangerZone.deleting': 'Eliminando…',
  'balances.dangerZone.confirmDeleteAll':
    'Esto elimina TODOS los participantes, eventos, recibos y balances. Esta acción no se puede deshacer.',
  'balances.dangerZone.deleteSuccess': 'Todos los datos fueron eliminados.',

  // Balance badge
  'balanceBadge.owed': 'le deben {amount}',
  'balanceBadge.owes': 'debe {amount}',
  'balanceBadge.settled': 'saldado',

  // Backend-originated error messages (translated on the frontend only — see
  // i18n/apiMessages.js for the matcher that maps a raw `detail` string onto
  // one of these keys). Neutral, professional Spanish — no voseo.
  'apiErrors.eventNotFound': 'El evento {id} no existe',
  'apiErrors.participantNotFound': 'El participante {id} no existe',
  'apiErrors.itemNotFound': 'El ítem {id} no existe',
  'apiErrors.receiptNotFound': 'El recibo {id} no existe',
  'apiErrors.payerNotInEvent':
    'El participante {participantId} no es participante del evento {eventId}; agréguelo primero mediante add_participant_to_event()',
  'apiErrors.assigneeNotInEvent':
    'El participante {participantId} no es participante del evento {eventId}; no se le puede asignar el ítem {itemId}',
  'apiErrors.sharesSumMismatch': 'Las partes de la asignación del ítem deben sumar 1.0; suman {total}',
  'apiErrors.assignmentRequired': 'Se requiere al menos una asignación para el ítem {itemId}',
  'apiErrors.duplicateParticipants': 'Hay ids de participantes duplicados en las asignaciones del ítem {itemId}',
  'apiErrors.shareNotPositive': 'La parte del participante {participantId} debe ser mayor que 0; es {share}',
  'apiErrors.participantHasPaidReceipts':
    'El participante {participantId} pagó uno o más recibos y no se puede eliminar (corrompería el historial de pagos)',
  'apiErrors.participantHasAssignments':
    'El participante {participantId} tiene una o más asignaciones de ítems y no se puede eliminar (corrompería el historial de consumo)',
  'apiErrors.receiptNoImage': 'El recibo {receiptId} no tiene una imagen almacenada; utilice la captura manual de ítems.',
  'apiErrors.uploadedFileEmpty': 'El archivo subido está vacío',
  'apiErrors.extraction.unsupportedFormat':
    'Este formato de archivo no es compatible con la extracción automática (formatos admitidos: JPEG, PNG, WEBP, GIF). Utilice la captura manual de ítems.',
  'apiErrors.extraction.unreadableImage':
    "No se pudo leer la imagen del recibo en '{path}'. Vuelva a intentarlo con la captura manual de ítems.",
  'apiErrors.extraction.timeout':
    'El servicio de extracción de recibos tardó demasiado en responder. Inténtelo de nuevo o utilice la captura manual de ítems.',
  'apiErrors.extraction.unavailable':
    'El servicio de extracción de recibos no está disponible en este momento. Utilice la captura manual de ítems.',
  'apiErrors.extraction.emptyResponse':
    'El servicio de extracción de recibos devolvió una respuesta vacía. Utilice la captura manual de ítems.',
  'apiErrors.extraction.unreadableResponse':
    'El servicio de extracción de recibos devolvió una respuesta ilegible. Utilice la captura manual de ítems.',
  'apiErrors.extraction.unexpectedFormat':
    'El servicio de extracción de recibos devolvió datos en un formato inesperado. Utilice la captura manual de ítems.',
  'apiErrors.extraction.imageNotFound':
    "No se encontró la imagen del recibo en '{path}'. Utilice la captura manual de ítems.",

  // Backend-originated warnings (vision.py's ExtractionResult.warnings[], via
  // the extraction proposal endpoint).
  'apiWarnings.itemsSumOverTotal':
    'La suma de los precios de los ítems supera el total del recibo ({itemsSum} > {receiptTotal}); verifique los montos antes de guardar.',
  'apiWarnings.itemsSumUnderTotal':
    'La suma de los precios de los ítems es muy inferior al total del recibo ({itemsSum} vs {receiptTotal}); es posible que falten ítems.',
};
