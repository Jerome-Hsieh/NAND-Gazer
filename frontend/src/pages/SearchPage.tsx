import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useProducts } from '../hooks/useProducts';
import ProductCard from '../components/ProductCard';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryParam = searchParams.get('q') ?? '';
  const pageParam = Number(searchParams.get('page')) || 1;

  const [input, setInput] = useState(queryParam);

  const { data, isLoading } = useProducts({
    search: queryParam || undefined,
    page: pageParam,
    page_size: 20,
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearchParams(input ? { q: input, page: '1' } : {});
  }

  function goToPage(page: number) {
    const params: Record<string, string> = { page: String(page) };
    if (queryParam) params.q = queryParam;
    setSearchParams(params);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Search Products</h1>

      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search products..."
          className="flex-1 glass-input"
        />
        <button
          type="submit"
          className="glass-button"
        >
          Search
        </button>
      </form>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton-dark p-4 animate-pulse">
              <div className="h-4 bg-white/10 rounded w-full mb-2" />
              <div className="h-6 bg-white/10 rounded w-20" />
            </div>
          ))}
        </div>
      ) : data?.items.length ? (
        <>
          <p className="text-sm text-white/50">
            Found {data.total} products (page {data.page} / {data.pages})
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {data.items.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex justify-center gap-2">
              <button
                onClick={() => goToPage(pageParam - 1)}
                disabled={pageParam <= 1}
                className="glass-pagination"
              >
                Previous
              </button>
              {Array.from({ length: Math.min(data.pages, 5) }, (_, i) => {
                const page = i + 1;
                return (
                  <button
                    key={page}
                    onClick={() => goToPage(page)}
                    className={`glass-pagination ${page === pageParam ? 'active' : ''}`}
                  >
                    {page}
                  </button>
                );
              })}
              <button
                onClick={() => goToPage(pageParam + 1)}
                disabled={pageParam >= (data?.pages ?? 1)}
                className="glass-pagination"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 text-white/40">
          <p>{queryParam ? 'No products found for this search.' : 'Enter a keyword to search.'}</p>
        </div>
      )}
    </div>
  );
}
