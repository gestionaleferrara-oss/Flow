import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value) {
  return new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR'
  }).format(Math.abs(value || 0));
}

export function formatNumber(value) {
  return new Intl.NumberFormat('it-IT').format(value || 0);
}

export function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).format(date);
  } catch {
    return dateStr;
  }
}

export function getStatusBadge(status) {
  switch (status) {
    case 'disponibile':
      return { label: 'Disponibile', color: 'text-green-500', icon: '✓' };
    case 'ordinare':
      return { label: 'Da Ordinare', color: 'text-amber-500', icon: '⚠' };
    case 'non_disponibile':
      return { label: 'Non Disponibile', color: 'text-red-500', icon: '✗' };
    default:
      return { label: status, color: 'text-gray-500', icon: '' };
  }
}
