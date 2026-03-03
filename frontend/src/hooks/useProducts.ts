import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProducts, getProduct, getPriceHistory, getStats, postScrape } from '../services/api';

export function useProducts(params: {
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  order?: string;
}) {
  return useQuery({
    queryKey: ['products', params],
    queryFn: () => getProducts(params),
  });
}

export function useProduct(id: number) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => getProduct(id),
    enabled: id > 0,
  });
}

export function usePriceHistory(id: number, days = 30) {
  return useQuery({
    queryKey: ['prices', id, days],
    queryFn: () => getPriceHistory(id, days),
    enabled: id > 0,
  });
}

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: 60_000,
  });
}

export function useScrape() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: postScrape,
    onSuccess: () => {
      // Background scrape takes ~10-20s; refresh data after a delay
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['products'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
      }, 15_000);
    },
  });
}
