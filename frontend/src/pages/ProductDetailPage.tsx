import { useParams, Link } from 'react-router-dom';
import { useProduct, usePriceHistory } from '../hooks/useProducts';
import PriceChart from '../components/PriceChart';

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const productId = Number(id) || 0;

  const { data: product, isLoading: productLoading } = useProduct(productId);
  const { data: prices, isLoading: pricesLoading } = usePriceHistory(productId);

  if (productLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-6 bg-white/10 rounded w-48" />
        <div className="space-y-4">
          <div className="h-8 bg-white/10 rounded w-3/4" />
          <div className="h-12 bg-white/10 rounded w-32" />
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="text-center py-12">
        <p className="text-white/50">Product not found</p>
        <Link to="/search" className="mt-4 inline-block text-blue-400 hover:text-blue-300 transition-colors">
          Back to search
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <Link to="/search" className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
        Back to search
      </Link>

      {/* Info */}
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-white">{product.name}</h1>

        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-red-600">
            NT${product.price?.toLocaleString() ?? '—'}
          </span>
          {product.original_price && product.original_price > (product.price ?? 0) && (
            <span className="text-lg text-white/30 line-through">
              NT${product.original_price.toLocaleString()}
            </span>
          )}
          {product.discount_percent && product.discount_percent > 0 && (
            <span className="text-sm bg-red-500/20 text-red-400 px-2 py-1 rounded font-medium">
              -{product.discount_percent}%
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm text-white/70 border-t border-white/10 pt-4">
          {product.shop_name && (
            <div>
              <span className="text-white/40">Shop:</span> {product.shop_name}
            </div>
          )}
          {product.brand && (
            <div>
              <span className="text-white/40">Brand:</span> {product.brand}
            </div>
          )}
          {product.platform && (
            <div>
              <span className="text-white/40">Platform:</span> {product.platform}
            </div>
          )}
        </div>

        {product.url && (
          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-2 glass-button"
          >
            View on PChome
          </a>
        )}
      </div>

      {/* Price Chart */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Price History (30 days)</h2>
        {pricesLoading ? (
          <div className="h-64 bg-white/5 rounded animate-pulse" />
        ) : (
          <PriceChart data={prices ?? []} />
        )}
      </div>
    </div>
  );
}
