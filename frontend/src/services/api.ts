import type { PaginatedProducts, ProductDetail, PricePoint, Stats } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function getProducts(params: {
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  order?: string;
}): Promise<PaginatedProducts> {
  const sp = new URLSearchParams();
  if (params.search) sp.set('search', params.search);
  if (params.page) sp.set('page', String(params.page));
  if (params.page_size) sp.set('page_size', String(params.page_size));
  if (params.sort_by) sp.set('sort_by', params.sort_by);
  if (params.order) sp.set('order', params.order);
  return fetchJson(`${API_BASE}/products?${sp}`);
}

export function getProduct(id: number): Promise<ProductDetail> {
  return fetchJson(`${API_BASE}/products/${id}`);
}

export function getPriceHistory(id: number, days = 30): Promise<PricePoint[]> {
  return fetchJson(`${API_BASE}/products/${id}/prices?days=${days}`);
}

export function getStats(): Promise<Stats> {
  return fetchJson(`${API_BASE}/stats`);
}
