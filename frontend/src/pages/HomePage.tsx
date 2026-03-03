import { Link } from 'react-router-dom';
import { useState } from 'react';
import { useStats, useProducts, useScrape } from '../hooks/useProducts';
import { useScrollReveal } from '../hooks/useScrollReveal';
import StatsCard from '../components/StatsCard';
import ProductCard from '../components/ProductCard';

export default function HomePage() {
  const { data: stats, isLoading: statsLoading } = useStats();
  const { data: products, isLoading: productsLoading } = useProducts({
    page: 1,
    page_size: 8,
    sort_by: 'updated_at',
    order: 'desc',
  });

  const scrape = useScrape();
  const [scrapeError, setScrapeError] = useState<string | null>(null);
  const [scrapeStarted, setScrapeStarted] = useState(false);

  const statsRef = useScrollReveal<HTMLDivElement>();
  const productsRef = useScrollReveal<HTMLDivElement>();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="mt-1 text-white/50">Overview of tracked product prices</p>
      </div>

      {/* Stats */}
      <div ref={statsRef} className="grid grid-cols-2 md:grid-cols-4 gap-4 scroll-reveal scroll-reveal-stagger">
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton-dark p-6 animate-pulse">
              <div className="h-4 bg-white/10 rounded w-24 mb-3" />
              <div className="h-8 bg-white/10 rounded w-16" />
            </div>
          ))
        ) : stats ? (
          <>
            <StatsCard title="Products Tracked" value={stats.total_products} />
            <StatsCard
              title="Tracking Keywords"
              value={stats.active_keywords}
              subtitle={stats.keyword_names.length > 0 ? stats.keyword_names.join(', ') : undefined}
            />
            <StatsCard title="Price Records" value={stats.total_price_records.toLocaleString()} />
            <StatsCard
              title="Last Scrape"
              value={stats.last_scrape_at ? new Date(stats.last_scrape_at).toLocaleDateString('zh-TW') : 'N/A'}
              subtitle={stats.prices_last_24h > 0 ? `${stats.prices_last_24h} prices in 24h` : undefined}
            />
          </>
        ) : null}
      </div>

      {/* Recent Products */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-white">Recently Updated</h2>
            <button
              onClick={() => {
                setScrapeError(null);
                setScrapeStarted(false);
                scrape.mutate(undefined, {
                  onSuccess: () => {
                    setScrapeStarted(true);
                    setTimeout(() => setScrapeStarted(false), 20000);
                  },
                  onError: (err) => {
                    setScrapeError(err instanceof Error ? err.message : 'Scrape failed');
                    setTimeout(() => setScrapeError(null), 5000);
                  },
                });
              }}
              disabled={scrape.isPending || scrapeStarted}
              className="px-3 py-1 text-xs font-medium rounded-md bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
            >
              {scrape.isPending ? (
                <span className="flex items-center gap-1">
                  <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Sending…
                </span>
              ) : scrapeStarted ? (
                <span className="flex items-center gap-1">
                  <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Updating…
                </span>
              ) : (
                'Update Now'
              )}
            </button>
            {scrapeError && (
              <span className="text-xs text-red-400">{scrapeError}</span>
            )}
          </div>
          <Link to="/search" className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
            View all →
          </Link>
        </div>
        {productsLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="skeleton-dark p-4 animate-pulse">
                <div className="h-4 bg-white/10 rounded w-full mb-2" />
                <div className="h-6 bg-white/10 rounded w-20" />
              </div>
            ))}
          </div>
        ) : products?.items.length ? (
          <div ref={productsRef} className="grid grid-cols-2 md:grid-cols-4 gap-4 scroll-reveal scroll-reveal-stagger">
            {products.items.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-white/40">
            <p>No products tracked yet. Run the Airflow scraper DAG to start collecting data.</p>
          </div>
        )}
      </div>
    </div>
  );
}
