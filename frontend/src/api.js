// Centralized fetch client for the ReciboSplit API. Every network call goes through here.

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function handleResponse(response) {
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const message = (data && data.detail) || `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return data;
}

async function requestJson(path, method = 'GET', body) {
  const hasBody = body !== undefined;
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: hasBody ? { 'Content-Type': 'application/json' } : undefined,
    body: hasBody ? JSON.stringify(body) : undefined,
  });
  return handleResponse(response);
}

async function requestForm(path, method, formData) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    body: formData,
  });
  return handleResponse(response);
}

export function createParticipant(name) {
  return requestJson('/participants', 'POST', { name });
}

export function getParticipants() {
  return requestJson('/participants');
}

export function createEvent(name, eventDate) {
  const body = eventDate ? { name, event_date: eventDate } : { name };
  return requestJson('/events', 'POST', body);
}

export function getEvents() {
  return requestJson('/events');
}

export function getEvent(eventId) {
  return requestJson(`/events/${eventId}`);
}

export function updateEventCurrency(eventId, currency) {
  return requestJson(`/events/${eventId}/currency`, 'PUT', { currency });
}

export function addParticipantToEvent(eventId, participantId) {
  return requestJson(`/events/${eventId}/participants`, 'POST', { participant_id: participantId });
}

export function uploadReceipt(eventId, { image, payerParticipantId, total }) {
  const formData = new FormData();
  formData.append('image', image);
  formData.append('payer_participant_id', payerParticipantId);
  formData.append('total', total);
  return requestForm(`/events/${eventId}/receipts`, 'POST', formData);
}

export function getEventReceipts(eventId) {
  return requestJson(`/events/${eventId}/receipts`);
}

export function addItems(receiptId, items) {
  return requestJson(`/receipts/${receiptId}/items`, 'POST', items);
}

export function getReceipt(receiptId) {
  return requestJson(`/receipts/${receiptId}`);
}

export function extractReceiptItems(receiptId) {
  return requestJson(`/receipts/${receiptId}/extract`, 'POST');
}

export function deleteItem(itemId) {
  return requestJson(`/items/${itemId}`, 'DELETE');
}

export function renameItem(itemId, description) {
  return requestJson(`/items/${itemId}`, 'PATCH', { description });
}

export function getItemAssignments(itemId) {
  return requestJson(`/items/${itemId}/assignments`);
}

export function setItemAssignments(itemId, assignments) {
  return requestJson(`/items/${itemId}/assignments`, 'PUT', assignments);
}

export function getEventBalances(eventId) {
  return requestJson(`/events/${eventId}/balances`);
}

export function getOverallBalances() {
  return requestJson('/balances');
}

export function deleteParticipant(participantId) {
  return requestJson(`/participants/${participantId}`, 'DELETE');
}

export function deleteEvent(eventId) {
  return requestJson(`/events/${eventId}`, 'DELETE');
}

export function deleteAllData() {
  return requestJson('/data', 'DELETE');
}

export function createSettlement(eventId, payload) {
  return requestJson(`/events/${eventId}/settlements`, 'POST', payload);
}

export function getEventSettlements(eventId) {
  return requestJson(`/events/${eventId}/settlements`);
}

export function deleteSettlement(settlementId) {
  return requestJson(`/settlements/${settlementId}`, 'DELETE');
}
